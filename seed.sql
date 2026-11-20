-- ============================================================================
-- SMART BLOOD BANK & EMERGENCY DONOR MATCHING SYSTEM
-- Seed Data Script (DML)
-- Contains realistic healthcare data, complete compatibility matrix,
-- inventory bags with dynamic relative dates, and emergency requisitions.
-- ============================================================================

USE smart_blood_bank;

-- Disable triggers and foreign key checks for clean seed population
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE donor_audit_log;
TRUNCATE TABLE request_allocations;
TRUNCATE TABLE emergency_requests;
TRUNCATE TABLE blood_inventory;
TRUNCATE TABLE donors;
TRUNCATE TABLE hospitals;
TRUNCATE TABLE blood_group_compatibility;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 1. SEED: BLOOD GROUP COMPATIBILITY (Full 64-Cell Matrix)
-- Based on Red Blood Cell (RBC) Antigen-Antibody Compatibility:
-- O- is the Universal Donor; AB+ is the Universal Recipient.
-- ============================================================================
INSERT INTO blood_group_compatibility (donor_group, recipient_group, is_compatible) VALUES
-- Donor O- (Universal Donor)
('O-', 'O-', TRUE), ('O-', 'O+', TRUE), ('O-', 'A-', TRUE), ('O-', 'A+', TRUE),
('O-', 'B-', TRUE), ('O-', 'B+', TRUE), ('O-', 'AB-', TRUE), ('O-', 'AB+', TRUE),

-- Donor O+
('O+', 'O-', FALSE), ('O+', 'O+', TRUE), ('O+', 'A-', FALSE), ('O+', 'A+', TRUE),
('O+', 'B-', FALSE), ('O+', 'B+', TRUE), ('O+', 'AB-', FALSE), ('O+', 'AB+', TRUE),

-- Donor A-
('A-', 'O-', FALSE), ('A-', 'O+', FALSE), ('A-', 'A-', TRUE), ('A-', 'A+', TRUE),
('A-', 'B-', FALSE), ('A-', 'B+', FALSE), ('A-', 'AB-', TRUE), ('A-', 'AB+', TRUE),

-- Donor A+
('A+', 'O-', FALSE), ('A+', 'O+', FALSE), ('A+', 'A-', FALSE), ('A+', 'A+', TRUE),
('A+', 'B-', FALSE), ('A+', 'B+', FALSE), ('A+', 'AB-', FALSE), ('A+', 'AB+', TRUE),

-- Donor B-
('B-', 'O-', FALSE), ('B-', 'O+', FALSE), ('B-', 'A-', FALSE), ('B-', 'A+', FALSE),
('B-', 'B-', TRUE), ('B-', 'B+', TRUE), ('B-', 'AB-', TRUE), ('B-', 'AB+', TRUE),

-- Donor B+
('B+', 'O-', FALSE), ('B+', 'O+', FALSE), ('B+', 'A-', FALSE), ('B+', 'A+', FALSE),
('B+', 'B-', FALSE), ('B+', 'B+', TRUE), ('B+', 'AB-', FALSE), ('B+', 'AB+', TRUE),

-- Donor AB-
('AB-', 'O-', FALSE), ('AB-', 'O+', FALSE), ('AB-', 'A-', FALSE), ('AB-', 'A+', FALSE),
('AB-', 'B-', FALSE), ('AB-', 'B+', FALSE), ('AB-', 'AB-', TRUE), ('AB-', 'AB+', TRUE),

-- Donor AB+ (Universal Recipient only accepts all, donates only to AB+)
('AB+', 'O-', FALSE), ('AB+', 'O+', FALSE), ('AB+', 'A-', FALSE), ('AB+', 'A+', FALSE),
('AB+', 'B-', FALSE), ('AB+', 'B+', FALSE), ('AB+', 'AB-', FALSE), ('AB+', 'AB+', TRUE);

-- ============================================================================
-- 2. SEED: HOSPITALS
-- Healthcare facilities across multiple cities and urgency tiers.
-- ============================================================================
INSERT INTO hospitals (hospital_id, hospital_code, name, license_number, city, address, contact_phone, contact_email, urgency_tier) VALUES
(1, 'HOSP-NYC-01', 'Mount Sinai Emergency & Trauma Center', 'LIC-NY-90211', 'New York', '1468 Madison Ave, New York, NY 10029', '+1-212-241-6500', 'bloodbank@mountsinai.org', 'Tier-1 Trauma Center'),
(2, 'HOSP-CHI-02', 'Northwestern Memorial Trauma Hospital', 'LIC-IL-44102', 'Chicago', '251 E Huron St, Chicago, IL 60611', '+1-312-926-2000', 'trauma.supply@nm.org', 'Tier-1 Trauma Center'),
(3, 'HOSP-SF-03',  'UCSF Helen Diller Medical Center',     'LIC-CA-88319', 'San Francisco', '505 Parnassus Ave, San Francisco, CA 94143', '+1-415-476-1000', 'bloodtransfusion@ucsf.edu', 'General Hospital'),
(4, 'HOSP-SEA-04', 'Harborview Regional Burn & Trauma',   'LIC-WA-12093', 'Seattle', '325 9th Ave, Seattle, WA 98104', '+1-206-744-3000', 'emergency.logistics@uw.edu', 'Tier-1 Trauma Center'),
(5, 'HOSP-NYC-05', 'NewYork-Presbyterian Hospital',        'LIC-NY-31084', 'New York', '525 E 68th St, New York, NY 10065', '+1-212-746-5454', 'bloodbank@nyp.org', 'Tier-1 Trauma Center'),
(6, 'HOSP-ATX-06', 'Dell Seton Medical Center at UT',      'LIC-TX-77401', 'Austin', '1500 Red River St, Austin, TX 78701', '+1-512-324-7000', 'or.supply@dellseton.org', 'General Hospital');

-- ============================================================================
-- 3. SEED: DONORS
-- Diverse blood groups, donation histories, and cooldown statuses.
-- Using relative dates to guarantee reproducible queries.
-- ============================================================================
INSERT INTO donors (donor_id, national_id, full_name, gender, date_of_birth, blood_group, phone, email, city, address, eligibility_status, medical_screening_notes, last_donation_date, total_donations) VALUES
(1,  'NID-90812301', 'Jonathan Doe',     'Male',   '1988-04-12', 'O-',  '+1-212-555-0101', 'jonathan.doe@email.com',     'New York',      '742 Evergreen Terrace, Brooklyn, NY', 'Eligible', 'Passed vitals check; BP 118/76, Hb 15.2 g/dL', DATE_SUB(CURRENT_DATE(), INTERVAL 125 DAY), 8),
(2,  'NID-90812302', 'Dr. Emily Watson', 'Female', '1992-09-24', 'O+',  '+1-312-555-0102', 'emily.watson@hospital.org',   'Chicago',       '310 N Michigan Ave, Chicago, IL',     'Eligible', 'Passed vitals check; BP 112/70, Hb 13.8 g/dL', DATE_SUB(CURRENT_DATE(), INTERVAL 110 DAY), 5),
(3,  'NID-90812303', 'Marcus Vance',     'Male',   '1985-11-03', 'A+',  '+1-212-555-0103', 'mvance@techcorp.io',         'New York',      '120 Broadway, New York, NY',          'Eligible', 'Passed vitals check; BP 122/80, Hb 14.5 g/dL', DATE_SUB(CURRENT_DATE(), INTERVAL 95 DAY),  3),
(4,  'NID-90812304', 'Sophia Lin',       'Female', '1996-02-18', 'B-',  '+1-415-555-0104', 'sophia.lin@baydesign.com',   'San Francisco', '88 Mission St, San Francisco, CA',    'Eligible', 'Recent donation on file; active 90-day cooldown', DATE_SUB(CURRENT_DATE(), INTERVAL 25 DAY),  2),
(5,  'NID-90812305', 'Carlos Ramirez',   'Male',   '2001-07-30', 'AB+', '+1-206-555-0105', 'carlos.r@seattleu.edu',      'Seattle',       '1100 E Pine St, Seattle, WA',         'Eligible', 'First-time registered donor; screening clear', NULL, 0),
(6,  'NID-90812306', 'Aisha Patel',      'Female', '1983-05-15', 'O-',  '+1-212-555-0106', 'aisha.patel@globalaid.org',  'New York',      '45 Wall St, New York, NY',            'Eligible', 'Universal hero donor; stellar health profile', DATE_SUB(CURRENT_DATE(), INTERVAL 160 DAY), 14),
(7,  'NID-90812307', 'David Kim',        'Male',   '1994-08-22', 'A-',  '+1-312-555-0107', 'dkim@fintechchicago.com',    'Chicago',       '600 W Adams St, Chicago, IL',         'Temporarily Ineligible', 'Low hemoglobin (11.4 g/dL); re-screen in 30 days', DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY),  4),
(8,  'NID-90812308', 'Rachel Green',     'Female', '1990-03-10', 'B+',  '+1-212-555-0108', 'rachel.green@manhattan.com', 'New York',      '200 Central Park West, NY',           'Eligible', 'Passed vitals check; BP 115/75, Hb 13.9 g/dL', DATE_SUB(CURRENT_DATE(), INTERVAL 105 DAY), 6),
(9,  'NID-90812309', 'Brian O\'Connor',  'Male',   '1989-12-01', 'AB-', '+1-512-555-0109', 'boconnor@austindata.io',     'Austin',        '500 W 2nd St, Austin, TX',            'Eligible', 'Passed vitals check; BP 120/78, Hb 15.0 g/dL', DATE_SUB(CURRENT_DATE(), INTERVAL 210 DAY), 7),
(10, 'NID-90812310', 'Elena Rostova',    'Female', '1995-06-19', 'O+',  '+1-212-555-0110', 'elena.rostova@nyu.edu',       'New York',      '70 Washington Sq, New York, NY',      'Eligible', 'Recent donor; in 90-day cooldown window', DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY),  1),
(11, 'NID-90812311', 'Tariq Al-Mansoor', 'Male',   '1987-10-14', 'A+',  '+1-206-555-0111', 'tariq.mansoor@techsea.com',  'Seattle',       '400 Terry Ave N, Seattle, WA',        'Eligible', 'Passed vitals check; BP 119/77, Hb 14.8 g/dL', DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY), 9),
(12, 'NID-90812312', 'Chloe Dubois',     'Female', '1993-01-29', 'O-',  '+1-415-555-0112', 'chloe.dubois@sftech.org',    'San Francisco', '350 California St, San Francisco, CA', 'Eligible', 'Universal donor; passed all serology checks', DATE_SUB(CURRENT_DATE(), INTERVAL 92 DAY),  4);

-- ============================================================================
-- 4. SEED: BLOOD INVENTORY
-- Realistic blood units with dynamically calculated collection and expiry dates:
-- Shelf life of Whole Blood / Packed RBCs = 42 Days.
-- Includes:
--   - Fresh units (Expiring in 20-35 days)
--   - Near-expiry units (Expiring in 2-5 days)
--   - Expired units (Past expiry date, status 'Available' to demonstrate ExpireOldBloodBags)
--   - Allocated units
-- ============================================================================
INSERT INTO blood_inventory (bag_id, bag_code, donor_id, blood_group, volume_ml, collection_date, expiry_date, hemoglobin_g_dl, storage_location, status) VALUES
-- O- Units (Universal / High Demand)
(1,  'BB-NY-2026-001', 1,  'O-',  450, DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY), INTERVAL 42 DAY), 14.8, 'Cold Storage Vault 1, Rack A1', 'Available'),
(2,  'BB-NY-2026-002', 6,  'O-',  500, DATE_SUB(CURRENT_DATE(), INTERVAL 15 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 15 DAY), INTERVAL 42 DAY), 15.1, 'Cold Storage Vault 1, Rack A2', 'Available'),
(3,  'BB-SF-2026-003', 12, 'O-',  450, DATE_SUB(CURRENT_DATE(), INTERVAL 39 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 39 DAY), INTERVAL 42 DAY), 13.9, 'Cold Storage Vault 1, Rack A3', 'Available'), -- Expiring in 3 days!
(4,  'BB-NY-2026-004', 1,  'O-',  450, DATE_SUB(CURRENT_DATE(), INTERVAL 48 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 48 DAY), INTERVAL 42 DAY), 14.5, 'Cold Storage Vault 1, Rack A4', 'Available'), -- EXPIRED 6 days ago!

-- O+ Units
(5,  'BB-CHI-2026-005', 2,  'O+', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 12 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 12 DAY), INTERVAL 42 DAY), 13.7, 'Cold Storage Vault 2, Rack B1', 'Available'),
(6,  'BB-NY-2026-006',  10, 'O+', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY), INTERVAL 42 DAY), 14.0, 'Cold Storage Vault 2, Rack B2', 'Available'),
(7,  'BB-CHI-2026-007', 2,  'O+', 500, DATE_SUB(CURRENT_DATE(), INTERVAL 50 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 50 DAY), INTERVAL 42 DAY), 13.5, 'Cold Storage Vault 2, Rack B3', 'Available'), -- EXPIRED 8 days ago!

-- A+ Units
(8,  'BB-NY-2026-008',  3,  'A+', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 8 DAY),  DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 8 DAY),  INTERVAL 42 DAY), 14.2, 'Cold Storage Vault 3, Rack C1', 'Available'),
(9,  'BB-SEA-2026-009', 11, 'A+', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 18 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 18 DAY), INTERVAL 42 DAY), 14.6, 'Cold Storage Vault 3, Rack C2', 'Available'),
(10, 'BB-NY-2026-010',  3,  'A+', 500, DATE_SUB(CURRENT_DATE(), INTERVAL 38 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 38 DAY), INTERVAL 42 DAY), 14.1, 'Cold Storage Vault 3, Rack C3', 'Available'), -- Expiring in 4 days!

-- A- Units
(11, 'BB-CHI-2026-011', 7,  'A-', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 20 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 20 DAY), INTERVAL 42 DAY), 13.2, 'Cold Storage Vault 3, Rack C4', 'Available'),

-- B+ Units
(12, 'BB-NY-2026-012',  8,  'B+', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 9 DAY),  DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 9 DAY),  INTERVAL 42 DAY), 13.8, 'Cold Storage Vault 4, Rack D1', 'Available'),
(13, 'BB-NY-2026-013',  8,  'B+', 500, DATE_SUB(CURRENT_DATE(), INTERVAL 22 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 22 DAY), INTERVAL 42 DAY), 14.0, 'Cold Storage Vault 4, Rack D2', 'Available'),

-- B- Units (Critically Low Stock - Only 1 unit in system!)
(14, 'BB-SF-2026-014',  4,  'B-', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 25 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 25 DAY), INTERVAL 42 DAY), 13.4, 'Cold Storage Vault 4, Rack D3', 'Available'),

-- AB- Units (Critically Low Stock - 1 unit)
(15, 'BB-ATX-2026-015', 9,  'AB-', 450, DATE_SUB(CURRENT_DATE(), INTERVAL 16 DAY), DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 16 DAY), INTERVAL 42 DAY), 15.0, 'Cold Storage Vault 5, Rack E1', 'Available'),

-- Already Allocated Units (Linked to fulfilled past emergency requests)
(16, 'BB-NY-2026-016',  6,  'O-',  450, DATE_SUB(CURRENT_DATE(), INTERVAL 5 DAY),  DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 5 DAY),  INTERVAL 42 DAY), 15.3, 'Cold Storage Vault 1, Rack A5', 'Allocated'),
(17, 'BB-NY-2026-017',  1,  'O-',  450, DATE_SUB(CURRENT_DATE(), INTERVAL 5 DAY),  DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 5 DAY),  INTERVAL 42 DAY), 14.9, 'Cold Storage Vault 1, Rack A6', 'Allocated');

-- ============================================================================
-- 5. SEED: EMERGENCY REQUESTS
-- Requisitions from hospitals demonstrating pending, partially fulfilled,
-- and fulfilled workflows with varying urgency tiers.
-- ============================================================================
INSERT INTO emergency_requests (request_id, request_code, hospital_id, patient_case_id, required_blood_group, units_requested, units_allocated, urgency_level, status, required_by_time, request_date, completion_date) VALUES
(1, 'REQ-2026-001', 1, 'CASE-NY-TRAUMA-8821', 'O-',  2, 2, 'CRITICAL', 'Fulfilled',           DATE_ADD(NOW(), INTERVAL 2 HOUR), DATE_SUB(NOW(), INTERVAL 4 HOUR), DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(2, 'REQ-2026-002', 2, 'CASE-CHI-SURG-4109',  'A+',  3, 0, 'HIGH',     'Pending',             DATE_ADD(NOW(), INTERVAL 6 HOUR), DATE_SUB(NOW(), INTERVAL 1 HOUR), NULL),
(3, 'REQ-2026-003', 3, 'CASE-SF-ICU-1044',    'B-',  1, 0, 'HIGH',     'Pending',             DATE_ADD(NOW(), INTERVAL 8 HOUR), DATE_SUB(NOW(), INTERVAL 2 HOUR), NULL),
(4, 'REQ-2026-004', 5, 'CASE-NY-CARDIAC-993',  'O+',  2, 0, 'CRITICAL', 'Pending',             DATE_ADD(NOW(), INTERVAL 1 HOUR), DATE_SUB(NOW(), INTERVAL 30 MINUTE), NULL),
(5, 'REQ-2026-005', 4, 'CASE-SEA-BURN-0021',   'AB+', 1, 0, 'ROUTINE',  'Pending',             DATE_ADD(NOW(), INTERVAL 24 HOUR), DATE_SUB(NOW(), INTERVAL 3 HOUR), NULL),
(6, 'REQ-2026-006', 6, 'CASE-ATX-MATERN-551',  'O-',  1, 0, 'CRITICAL', 'Pending',             DATE_ADD(NOW(), INTERVAL 2 HOUR), DATE_SUB(NOW(), INTERVAL 15 MINUTE), NULL);

-- ============================================================================
-- 6. SEED: REQUEST ALLOCATIONS
-- Record existing fulfilled emergency request allocations.
-- ============================================================================
INSERT INTO request_allocations (allocation_id, request_id, bag_id, allocated_at, allocated_by, dispatch_status) VALUES
(1, 1, 16, DATE_SUB(NOW(), INTERVAL 2 HOUR), 'DR_CHEN_DISPATCHER', 'Dispatched'),
(2, 1, 17, DATE_SUB(NOW(), INTERVAL 2 HOUR), 'DR_CHEN_DISPATCHER', 'Dispatched');

-- ============================================================================
-- 7. SEED: DONOR AUDIT LOG
-- Regulatory trail of previous intake screening notes and status updates.
-- ============================================================================
INSERT INTO donor_audit_log (donor_id, old_eligibility_status, new_eligibility_status, old_medical_notes, new_medical_notes, action_type, changed_by, changed_at) VALUES
(7, 'Eligible', 'Temporarily Ineligible', 'Passed routine check', 'Low hemoglobin (11.4 g/dL); re-screen in 30 days', 'STATUS_CHANGE', 'DR_MARTINEZ_MD', DATE_SUB(NOW(), INTERVAL 45 DAY)),
(1, 'Eligible', 'Eligible', 'Initial registration', 'Passed vitals check; BP 118/76, Hb 15.2 g/dL', 'NOTE_UPDATE', 'SYSTEM_ADMIN', DATE_SUB(NOW(), INTERVAL 125 DAY));
