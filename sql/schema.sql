-- GCV CRM — re-normalised 3NF schema (SQLite)
-- Keys are CHAR(8): 3-letter table code + 5-digit number.
-- Dimension FKs use ON DELETE RESTRICT (default); entity parent->child chains
-- use ON DELETE CASCADE.
PRAGMA foreign_keys = ON;

-- ============ Dimension tables (one row per distinct value) ============
CREATE TABLE City          (city_id          CHAR(8) PRIMARY KEY, city_name        VARCHAR(50) NOT NULL);
CREATE TABLE JobTitle      (job_title_id     CHAR(8) PRIMARY KEY, job_title_name   VARCHAR(50) NOT NULL);
CREATE TABLE Industry      (industry_id      CHAR(8) PRIMARY KEY, industry_name    VARCHAR(50) NOT NULL);
CREATE TABLE LeadSource    (lead_source_id   CHAR(8) PRIMARY KEY, lead_source      VARCHAR(50) NOT NULL);
CREATE TABLE LeadStatus    (lead_status_id   CHAR(8) PRIMARY KEY, lead_status      VARCHAR(50) NOT NULL);
CREATE TABLE LostReason    (lost_reason_id   CHAR(8) PRIMARY KEY, lost_reason      VARCHAR(50) NOT NULL);
CREATE TABLE QuoteStatus   (quote_status_id  CHAR(8) PRIMARY KEY, quote_status     VARCHAR(50) NOT NULL);
CREATE TABLE PaymentMethod (payment_method_id CHAR(8) PRIMARY KEY, payment_method  VARCHAR(50) NOT NULL);
CREATE TABLE PaymentStatus (payment_status_id CHAR(8) PRIMARY KEY, payment_status  VARCHAR(50) NOT NULL);
CREATE TABLE OrderStatus   (order_status_id  CHAR(8) PRIMARY KEY, status_name      VARCHAR(50) NOT NULL);
CREATE TABLE Warranty      (warranty_id      CHAR(8) PRIMARY KEY, warranty         VARCHAR(50) NOT NULL);
CREATE TABLE VehicleType   (vehicle_type_id  CHAR(8) PRIMARY KEY, vehicle_type     VARCHAR(50) NOT NULL);
CREATE TABLE FuelType      (fuel_type_id     CHAR(8) PRIMARY KEY, fuel_type        VARCHAR(50) NOT NULL);
CREATE TABLE Role          (role_id          CHAR(8) PRIMARY KEY, role             VARCHAR(50) NOT NULL);
CREATE TABLE Stage         (stage_id         CHAR(8) PRIMARY KEY, stage            VARCHAR(50) NOT NULL);

-- ============ Address tables (reference unified City) ============
CREATE TABLE BillingAddress (
    billing_address_id CHAR(8) PRIMARY KEY,
    billing_address    VARCHAR(50) UNIQUE NOT NULL,
    city_id            CHAR(8),
    FOREIGN KEY (city_id) REFERENCES City(city_id)
);
CREATE TABLE ShippingAddress (
    shipping_address_id CHAR(8) PRIMARY KEY,
    shipping_address    VARCHAR(50) UNIQUE NOT NULL,
    city_id             CHAR(8),
    FOREIGN KEY (city_id) REFERENCES City(city_id)
);

-- ============ Core entities ============
CREATE TABLE Users (
    user_id            CHAR(8) PRIMARY KEY,
    user_name          VARCHAR(100) NOT NULL,
    user_email_address VARCHAR(100) UNIQUE NOT NULL,
    user_phone_number  VARCHAR(15) NOT NULL,
    role_id            CHAR(8),
    commission_rate    VARCHAR(2),
    FOREIGN KEY (role_id) REFERENCES Role(role_id)
);

CREATE TABLE Account (
    account_id            CHAR(8) PRIMARY KEY,
    account_name          VARCHAR(50) NOT NULL,
    account_email_address VARCHAR(100) NOT NULL,
    account_mobile_number VARCHAR(15) NOT NULL,
    billing_address_id    CHAR(8),
    user_id               CHAR(8),
    account_status        BOOLEAN DEFAULT TRUE,
    annual_revenue        INTEGER,
    industry_id           CHAR(8),
    FOREIGN KEY (user_id)            REFERENCES Users(user_id),
    FOREIGN KEY (billing_address_id) REFERENCES BillingAddress(billing_address_id),
    FOREIGN KEY (industry_id)        REFERENCES Industry(industry_id)
);

CREATE TABLE Customer (
    customer_id            CHAR(8) PRIMARY KEY,
    customer_name          VARCHAR(50) NOT NULL,
    customer_email_address VARCHAR(100) UNIQUE NOT NULL,
    customer_mobile_number VARCHAR(15) NOT NULL,
    account_id             CHAR(8),
    job_title_id           CHAR(8),
    FOREIGN KEY (job_title_id) REFERENCES JobTitle(job_title_id),
    FOREIGN KEY (account_id)   REFERENCES Account(account_id) ON DELETE CASCADE
);

CREATE TABLE Lead (
    lead_id        CHAR(8) PRIMARY KEY,
    created_date   DATE NOT NULL,
    lead_score     INTEGER CHECK (lead_score BETWEEN 1 AND 100),
    account_id     CHAR(8),
    lead_source_id CHAR(8),
    lead_status_id CHAR(8),
    user_id        CHAR(8),
    customer_id    CHAR(8),
    FOREIGN KEY (customer_id)    REFERENCES Customer(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)        REFERENCES Users(user_id),
    FOREIGN KEY (lead_source_id) REFERENCES LeadSource(lead_source_id),
    FOREIGN KEY (lead_status_id) REFERENCES LeadStatus(lead_status_id)
);

CREATE TABLE Product (
    product_id      CHAR(8) PRIMARY KEY,
    product_name    VARCHAR(50) NOT NULL,
    vehicle_type_id CHAR(8),
    model_year      INTEGER,
    base_price      INTEGER NOT NULL,
    inventory_level INTEGER CHECK (inventory_level >= 0),
    fuel_type_id    CHAR(8),
    weight_capacity INTEGER CHECK (weight_capacity >= 0),
    dimensions      VARCHAR(50),
    FOREIGN KEY (fuel_type_id)    REFERENCES FuelType(fuel_type_id),
    FOREIGN KEY (vehicle_type_id) REFERENCES VehicleType(vehicle_type_id)
);

CREATE TABLE Opportunity (
    opportunity_id      CHAR(8) PRIMARY KEY,
    close_date          DATE,
    expected_close_date DATE,
    opportunity_amount  DECIMAL(10,2) NOT NULL,
    lost_reason_id      CHAR(8),
    stage_id            CHAR(8),
    product_id          CHAR(8),
    user_id             CHAR(8),
    lead_id             CHAR(8),
    customer_id         CHAR(8),
    FOREIGN KEY (customer_id)    REFERENCES Customer(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)        REFERENCES Users(user_id),
    FOREIGN KEY (lead_id)        REFERENCES Lead(lead_id) ON DELETE CASCADE,
    FOREIGN KEY (stage_id)       REFERENCES Stage(stage_id),
    FOREIGN KEY (product_id)     REFERENCES Product(product_id),
    FOREIGN KEY (lost_reason_id) REFERENCES LostReason(lost_reason_id)
);

CREATE TABLE Quote (
    quote_id        CHAR(8) PRIMARY KEY,
    expiration_date DATE,            -- only revised quotes carry an expiry (per spec)
    discount        INTEGER CHECK (discount BETWEEN 0 AND 25),
    total_amount    DECIMAL(10,2) NOT NULL,
    created_date    DATE NOT NULL,
    revision_number INTEGER DEFAULT 1,
    quote_status_id CHAR(8),
    opportunity_id  CHAR(8),
    FOREIGN KEY (quote_status_id) REFERENCES QuoteStatus(quote_status_id),
    FOREIGN KEY (opportunity_id)  REFERENCES Opportunity(opportunity_id) ON DELETE CASCADE
);

CREATE TABLE Orders (
    order_id               CHAR(8) PRIMARY KEY,
    order_date             DATE NOT NULL,
    order_status_id        CHAR(8),
    expected_delivery_date DATE,
    delivery_date          DATE,
    quote_id               CHAR(8),
    shipping_address_id    CHAR(8),
    FOREIGN KEY (shipping_address_id) REFERENCES ShippingAddress(shipping_address_id),
    FOREIGN KEY (quote_id)            REFERENCES Quote(quote_id) ON DELETE CASCADE,
    FOREIGN KEY (order_status_id)     REFERENCES OrderStatus(order_status_id)
);

CREATE TABLE Invoice (
    invoice_id        CHAR(8) PRIMARY KEY,
    invoice_date      DATE NOT NULL,
    due_date          DATE NOT NULL,
    total_amount      INTEGER,
    late_fees         DECIMAL(10,2) DEFAULT 0,
    discount_applied  DECIMAL(10,2) DEFAULT 0,
    order_id          CHAR(8),
    payment_status_id CHAR(8),
    payment_method_id CHAR(8),
    payment_date      DATE,
    final_amount      INTEGER,
    FOREIGN KEY (payment_status_id) REFERENCES PaymentStatus(payment_status_id),
    FOREIGN KEY (payment_method_id) REFERENCES PaymentMethod(payment_method_id),
    FOREIGN KEY (order_id)          REFERENCES Orders(order_id) ON DELETE CASCADE
);

CREATE TABLE QuoteLineItem (
    line_item_id CHAR(8) PRIMARY KEY,
    quote_id     CHAR(8),
    product_id   CHAR(8),
    quantity     INTEGER CHECK (quantity BETWEEN 1 AND 20),
    unit_price   DECIMAL(10,2) NOT NULL,
    total_price  DECIMAL(10,2) NOT NULL,
    warranty_id  CHAR(8),
    FOREIGN KEY (product_id)  REFERENCES Product(product_id),
    FOREIGN KEY (quote_id)    REFERENCES Quote(quote_id) ON DELETE CASCADE,
    FOREIGN KEY (warranty_id) REFERENCES Warranty(warranty_id)
);
