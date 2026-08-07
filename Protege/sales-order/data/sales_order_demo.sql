CREATE DATABASE sales_order_demo CHARACTER SET utf8mb4;
USE sales_order_demo;

-- ============
-- DIM 层：维度表
-- ============

CREATE TABLE sales_order_demo.dim_customer (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(50),
    city VARCHAR(50)
);

INSERT INTO sales_order_demo.dim_customer VALUES
(1, '阿里', '杭州'),
(2, '腾讯', '深圳');

CREATE TABLE sales_order_demo.dim_product (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(50),
    category VARCHAR(50)
);

INSERT INTO sales_order_demo.dim_product VALUES
(101, '云服务器', 'IaaS'),
(102, '数据库RDS', 'PaaS');

-- ============
-- DWD 层：明细事实
-- ============

CREATE TABLE sales_order_demo.dwd_sales_order_detail (
    order_id INT,
    customer_id INT,
    product_id INT,
    quantity INT,
    unit_price DECIMAL(10,2),
    order_date DATE
);

INSERT INTO sales_order_demo.dwd_sales_order_detail VALUES
(1001, 1, 101, 2, 3000.00, '2025-01-01'),
(1002, 2, 102, 5, 1200.00, '2025-01-02');

-- ============
-- DWS 层：汇总事实
-- ============

CREATE TABLE sales_order_demo.dws_sales_order_stat_daily (
    stat_date DATE,
    product_id INT,
    total_quantity INT,
    total_amount DECIMAL(12,2)
);

INSERT INTO sales_order_demo.dws_sales_order_stat_daily VALUES
('2025-01-01', 101, 2, 6000.00),
('2025-01-02', 102, 5, 6000.00);

-- ============
-- ADS 层：指标报表
-- ============

CREATE TABLE sales_order_demo.ads_sales_summary (
    report_month CHAR(7),
    total_amount DECIMAL(14,2)
);

INSERT INTO sales_order_demo.ads_sales_summary VALUES
('2025-01', 12000.00);