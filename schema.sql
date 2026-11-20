-- ============================================================================
-- SMART BLOOD BANK & EMERGENCY DONOR MATCHING SYSTEM
-- Database Definition Script (DDL)
-- Normalized up to 3NF / BCNF
-- Target Engine: MySQL 8.0+ / InnoDB
-- ============================================================================

CREATE DATABASE IF NOT EXISTS smart_blood_bank
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_blood_bank;

-- Disable Foreign Key checks temporarily for clean drop order
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS donor_audit_log;
DROP TABLE IF EXISTS request_allocations;
DROP TABLE IF EXISTS emergency_requests;
DROP TABLE IF EXISTS blood_inventory;
DROP TABLE IF EXISTS donors;
DROP TABLE IF EXISTS hospitals;
DROP TABLE IF EXISTS blood_group_compatibility;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 1. BLOOD GROUP COMPATIBILITY (Lookup Matrix Table - 3NF)
-- Defines medically validated Red Blood Cell (RBC) transfusion compatibility rules.
-- Eliminates transitive dependencies in compatibility calculations.
-- ============================================================================
CREATE TABLE blood_group_compatibility (
    donor_group VARCHAR(5) NOT NULL,
    recipient_group VARCHAR(5) NOT NULL,
    is_compatible BOOLEAN NOT NULL DEFAULT TRUE,
    
    PRIMARY KEY (donor_group, recipient_group),
    INDEX idx_compat_recipient (recipient_group, is_compatible)
) ENGINE=InnoDB;

-- ============================================================================
-- 2. HOSPITALS (Healthcare Provider Entities)
-- Stores verified partner medical centers, trauma units, and clinics.
-- ============================================================================
CREATE TABLE hospitals (
    hospital_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    license_number VARCHAR(50) NOT NULL UNIQUE,
    city VARCHAR(80) NOT NULL,
    address VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(25) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    urgency_tier ENUM('Tier-1 Trauma Center', 'General Hospital', 'Specialty Clinic') NOT NULL DEFAULT 'General Hospital',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_hospital_city (city),
    INDEX idx_hospital_tier (urgency_tier)
) ENGINE=InnoDB;

-- ============================================================================
-- 3. DONORS (Voluntary Blood Donors & Medical Records)
-- Tracks donor identity, blood group, eligibility, and cooldown state.
-- ============================================================================
CREATE TABLE donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    national_id VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    date_of_birth DATE NOT NULL,
    blood_group ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    phone VARCHAR(25) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    city VARCHAR(80) NOT NULL,
    address VARCHAR(255),
    eligibility_status ENUM('Eligible', 'Temporarily Ineligible', 'Permanently Ineligible') NOT NULL DEFAULT 'Eligible',
    medical_screening_notes VARCHAR(255) NOT NULL DEFAULT 'Passed standard vitals and hemoglobin check',
    last_donation_date DATE DEFAULT NULL,
    total_donations INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_total_donations CHECK (total_donations >= 0),
    INDEX idx_donors_blood_city (blood_group, city, eligibility_status),
    INDEX idx_donors_last_donation (last_donation_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 4. BLOOD INVENTORY (Physical Blood Bags Tracking)
-- Tracks each collected whole blood unit with collection date, volume,
-- calculated expiration date (42 days shelf life), and storage location.
-- ============================================================================
CREATE TABLE blood_inventory (
    bag_id INT AUTO_INCREMENT PRIMARY KEY,
    bag_code VARCHAR(30) NOT NULL UNIQUE,
    donor_id INT NOT NULL,
    blood_group ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    volume_ml INT NOT NULL DEFAULT 450,
    collection_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    hemoglobin_g_dl DECIMAL(4,1) NOT NULL DEFAULT 13.5,
    storage_location VARCHAR(60) NOT NULL DEFAULT 'Cold Room 1, Shelf A',
    status ENUM('Available', 'Allocated', 'Transfused', 'Expired', 'Discarded') NOT NULL DEFAULT 'Available',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_inventory_donor 
        FOREIGN KEY (donor_id) REFERENCES donors(donor_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_bag_volume 
        CHECK (volume_ml BETWEEN 350 AND 550),
    CONSTRAINT chk_bag_hemoglobin 
        CHECK (hemoglobin_g_dl >= 12.0),
    CONSTRAINT chk_bag_expiry 
        CHECK (expiry_date >= collection_date),
        
    INDEX idx_inv_status_blood_expiry (status, blood_group, expiry_date),
    INDEX idx_inv_expiry (expiry_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 5. EMERGENCY REQUESTS (Hospital Blood Requisitions)
-- Real-time requisition pipeline from hospitals requiring blood units.
-- ============================================================================
CREATE TABLE emergency_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    request_code VARCHAR(30) NOT NULL UNIQUE,
    hospital_id INT NOT NULL,
    patient_case_id VARCHAR(50) NOT NULL,
    required_blood_group ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    units_requested INT UNSIGNED NOT NULL,
    units_allocated INT UNSIGNED NOT NULL DEFAULT 0,
    urgency_level ENUM('CRITICAL', 'HIGH', 'MEDIUM', 'ROUTINE') NOT NULL DEFAULT 'HIGH',
    status ENUM('Pending', 'Partially Fulfilled', 'Fulfilled', 'Cancelled') NOT NULL DEFAULT 'Pending',
    required_by_time DATETIME NOT NULL,
    request_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completion_date DATETIME DEFAULT NULL,
    
    CONSTRAINT fk_request_hospital 
        FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_units_requested 
        CHECK (units_requested > 0),
    CONSTRAINT chk_units_allocated 
        CHECK (units_allocated <= units_requested),
        
    INDEX idx_req_status_urgency (status, urgency_level, request_date)
) ENGINE=InnoDB;

-- ============================================================================
-- 6. REQUEST ALLOCATIONS (Transactional Bridge: Requests <-> Blood Bags)
-- Strict 1-to-1 bag allocation mapping ensuring no bag is double-allocated.
-- ============================================================================
CREATE TABLE request_allocations (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    bag_id INT NOT NULL UNIQUE,
    allocated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    allocated_by VARCHAR(60) NOT NULL DEFAULT 'SYSTEM_TRANSACTION',
    dispatch_status ENUM('Dispatched', 'In Transit', 'Received', 'Cancelled') NOT NULL DEFAULT 'Dispatched',
    
    CONSTRAINT fk_alloc_request 
        FOREIGN KEY (request_id) REFERENCES emergency_requests(request_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_alloc_bag 
        FOREIGN KEY (bag_id) REFERENCES blood_inventory(bag_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
        
    INDEX idx_alloc_request (request_id)
) ENGINE=InnoDB;

-- ============================================================================
-- 7. DONOR AUDIT LOG (Medical & Eligibility Audit Trail)
-- Captures regulatory compliance events whenever donor status changes.
-- ============================================================================
CREATE TABLE donor_audit_log (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    old_eligibility_status VARCHAR(50),
    new_eligibility_status VARCHAR(50),
    old_medical_notes VARCHAR(255),
    new_medical_notes VARCHAR(255),
    action_type ENUM('STATUS_CHANGE', 'NOTE_UPDATE', 'DONATION_RECORDED', 'RESTRICTION_APPLIED') NOT NULL,
    changed_by VARCHAR(60) NOT NULL DEFAULT 'SYSTEM',
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_audit_donor 
        FOREIGN KEY (donor_id) REFERENCES donors(donor_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_audit_donor_time (donor_id, changed_at)
) ENGINE=InnoDB;
