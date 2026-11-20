-- ============================================================================
-- SMART BLOOD BANK & EMERGENCY DONOR MATCHING SYSTEM
-- Advanced Database Logic: Triggers, Stored Procedures, and Views
-- ============================================================================

USE smart_blood_bank;

-- ============================================================================
-- 1. TRIGGERS
-- ============================================================================

-- Drop existing triggers if present
DROP TRIGGER IF EXISTS trg_after_allocation_insert;
DROP TRIGGER IF EXISTS trg_after_allocation_delete;
DROP TRIGGER IF EXISTS trg_donor_status_audit;

DELIMITER $$

-- ----------------------------------------------------------------------------
-- Trigger 1: Automatic Blood Bag Allocation & Request Status Sync
-- Fires immediately upon an allocation being committed.
-- Marks the specific blood bag as 'Allocated' and increments requisition counts.
-- Sets request status to 'Fulfilled' when requested units are met.
-- ----------------------------------------------------------------------------
CREATE TRIGGER trg_after_allocation_insert
AFTER INSERT ON request_allocations
FOR EACH ROW
BEGIN
    -- 1. Mark the assigned blood bag as Allocated
    UPDATE blood_inventory
    SET status = 'Allocated'
    WHERE bag_id = NEW.bag_id;

    -- 2. Increment fulfilled units and update requisition status
    UPDATE emergency_requests
    SET units_allocated = units_allocated + 1,
        status = CASE
            WHEN units_allocated + 1 >= units_requested THEN 'Fulfilled'
            ELSE 'Partially Fulfilled'
        END,
        completion_date = CASE
            WHEN units_allocated + 1 >= units_requested THEN NOW()
            ELSE completion_date
        END
    WHERE request_id = NEW.request_id;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 1b (Reversal Safeguard): De-allocation / Cancellation Trigger
-- Reverts bag status to 'Available' and decrements emergency request counts
-- if an allocation is removed or rolled back.
-- ----------------------------------------------------------------------------
CREATE TRIGGER trg_after_allocation_delete
AFTER DELETE ON request_allocations
FOR EACH ROW
BEGIN
    -- Revert bag status back to Available
    UPDATE blood_inventory
    SET status = 'Available'
    WHERE bag_id = OLD.bag_id;

    -- Decrement fulfilled count on the requisition
    UPDATE emergency_requests
    SET units_allocated = GREATEST(0, CAST(units_allocated AS SIGNED) - 1),
        status = CASE
            WHEN CAST(units_allocated AS SIGNED) - 1 <= 0 THEN 'Pending'
            ELSE 'Partially Fulfilled'
        END,
        completion_date = NULL
    WHERE request_id = OLD.request_id;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 2: Regulatory Donor Audit Log
-- Fires on donor record updates. Captures historical modifications to
-- eligibility statuses, deferrals, and medical screening notes.
-- ----------------------------------------------------------------------------
CREATE TRIGGER trg_donor_status_audit
AFTER UPDATE ON donors
FOR EACH ROW
BEGIN
    IF (OLD.eligibility_status <> NEW.eligibility_status) 
       OR (OLD.medical_screening_notes <> NEW.medical_screening_notes) THEN
       
        INSERT INTO donor_audit_log (
            donor_id,
            old_eligibility_status,
            new_eligibility_status,
            old_medical_notes,
            new_medical_notes,
            action_type,
            changed_by,
            changed_at
        ) VALUES (
            NEW.donor_id,
            OLD.eligibility_status,
            NEW.eligibility_status,
            OLD.medical_screening_notes,
            NEW.medical_screening_notes,
            CASE
                WHEN OLD.eligibility_status <> NEW.eligibility_status THEN 'STATUS_CHANGE'
                ELSE 'NOTE_UPDATE'
            END,
            COALESCE(CURRENT_USER(), 'SYSTEM'),
            NOW()
        );
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- 2. STORED PROCEDURES
-- ============================================================================

DROP PROCEDURE IF EXISTS MatchCompatibleDonors;
DROP PROCEDURE IF EXISTS ExpireOldBloodBags;

DELIMITER $$

-- ----------------------------------------------------------------------------
-- Stored Procedure 1: Smart Compatible Donor Matchmaker
-- Takes hospital ID and requested blood group.
-- Cross-references blood_group_compatibility to find all eligible donors
-- whose 90-day cooldown period has elapsed.
-- Prioritizes local donors residing in the requesting hospital's city.
-- ----------------------------------------------------------------------------
CREATE PROCEDURE MatchCompatibleDonors(
    IN p_hospital_id INT,
    IN p_required_blood_group VARCHAR(5)
)
BEGIN
    DECLARE v_hospital_city VARCHAR(80);
    DECLARE v_hospital_name VARCHAR(150);

    -- Fetch hospital location details
    SELECT name, city 
    INTO v_hospital_name, v_hospital_city
    FROM hospitals
    WHERE hospital_id = p_hospital_id;

    -- Query compatible, eligible donors outside cooldown
    SELECT 
        d.donor_id,
        d.full_name,
        d.blood_group AS donor_blood_group,
        p_required_blood_group AS patient_blood_group,
        d.phone,
        d.email,
        d.city,
        v_hospital_city AS hospital_city,
        CASE 
            WHEN LOWER(d.city) = LOWER(v_hospital_city) THEN 'Local (Same City)'
            ELSE 'Regional / Transfer Required'
        END AS proximity_status,
        d.last_donation_date,
        CASE 
            WHEN d.last_donation_date IS NULL THEN 'First-time Donor'
            ELSE CONCAT(DATEDIFF(CURRENT_DATE(), d.last_donation_date), ' days ago')
        END AS donation_history,
        d.total_donations
    FROM donors d
    INNER JOIN blood_group_compatibility bgc 
        ON d.blood_group = bgc.donor_group
    WHERE bgc.recipient_group = p_required_blood_group
      AND bgc.is_compatible = TRUE
      AND d.eligibility_status = 'Eligible'
      AND (
          d.last_donation_date IS NULL 
          OR DATEDIFF(CURRENT_DATE(), d.last_donation_date) >= 90
      )
    ORDER BY 
        (CASE WHEN LOWER(d.city) = LOWER(v_hospital_city) THEN 0 ELSE 1 END) ASC,
        (CASE WHEN d.last_donation_date IS NULL THEN 0 ELSE 1 END) ASC,
        d.last_donation_date ASC,
        d.total_donations DESC;
END$$

-- ----------------------------------------------------------------------------
-- Stored Procedure 2: Automated Blood Unit Expiration Check
-- Identifies all 'Available' blood units that have exceeded their 42-day lifespan
-- and updates their status to 'Expired'.
-- Returns count and a result set of affected units.
-- ----------------------------------------------------------------------------
CREATE PROCEDURE ExpireOldBloodBags(
    OUT p_expired_count INT
)
BEGIN
    -- 1. Perform bulk status transition for past-due units
    UPDATE blood_inventory
    SET status = 'Expired'
    WHERE status = 'Available'
      AND expiry_date < CURRENT_DATE();

    -- 2. Store affected row count in OUT parameter
    SET p_expired_count = ROW_COUNT();

    -- 3. Return result set of newly or currently expired bags for audit display
    SELECT 
        bag_id,
        bag_code,
        blood_group,
        collection_date,
        expiry_date,
        DATEDIFF(CURRENT_DATE(), expiry_date) AS days_expired,
        storage_location,
        status
    FROM blood_inventory
    WHERE status = 'Expired'
    ORDER BY expiry_date ASC;
END$$

DELIMITER ;

-- ============================================================================
-- 3. VIEWS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- View 1: AvailableBloodStockView
-- Aggregates non-expired, unallocated blood units ready for immediate transfusion.
-- Groups by blood type with total volume and earliest shelf expiration date.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW AvailableBloodStockView AS
SELECT 
    bi.blood_group,
    COUNT(bi.bag_id) AS units_available,
    SUM(bi.volume_ml) AS total_volume_ml,
    MIN(bi.collection_date) AS oldest_collection_date,
    MIN(bi.expiry_date) AS earliest_expiry_date,
    DATEDIFF(MIN(bi.expiry_date), CURRENT_DATE()) AS days_until_next_expiry
FROM blood_inventory bi
WHERE bi.status = 'Available' 
  AND bi.expiry_date >= CURRENT_DATE()
GROUP BY bi.blood_group;

-- ----------------------------------------------------------------------------
-- View 2: CriticalShortageView
-- Identifies inventory crisis points: blood groups with fewer than 3 available units.
-- Uses an exhaustive blood group domain union so blood types with ZERO stock
-- are still displayed with 'CRITICAL (EMPTY)' rather than disappearing.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW CriticalShortageView AS
SELECT 
    bg.blood_group,
    COALESCE(v.units_available, 0) AS current_stock_units,
    COALESCE(v.total_volume_ml, 0) AS total_volume_ml,
    v.earliest_expiry_date,
    CASE 
        WHEN COALESCE(v.units_available, 0) = 0 THEN 'CRITICAL (EMPTY)'
        WHEN COALESCE(v.units_available, 0) = 1 THEN 'EXTREME SHORTAGE'
        ELSE 'LOW STOCK WARNING'
    END AS shortage_severity,
    GREATEST(0, 3 - COALESCE(v.units_available, 0)) AS units_needed_to_safe_threshold
FROM (
    SELECT 'A+' AS blood_group UNION ALL
    SELECT 'A-' UNION ALL
    SELECT 'B+' UNION ALL
    SELECT 'B-' UNION ALL
    SELECT 'AB+' UNION ALL
    SELECT 'AB-' UNION ALL
    SELECT 'O+' UNION ALL
    SELECT 'O-'
) bg
LEFT JOIN AvailableBloodStockView v ON bg.blood_group = v.blood_group
WHERE COALESCE(v.units_available, 0) < 3
ORDER BY current_stock_units ASC, bg.blood_group ASC;
