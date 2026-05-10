
CREATE TABLE IF NOT EXISTS patents (
    patent_id VARCHAR(255) PRIMARY KEY,
    title TEXT,
    abstract TEXT,
    filing_date VARCHAR(50),
    year INT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventors (
    inventor_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500),
    country VARCHAR(100)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS companies (
    company_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS relationships (
    patent_id VARCHAR(255),
    inventor_id VARCHAR(255),
    company_id VARCHAR(255),
    FOREIGN KEY (patent_id) REFERENCES patents(patent_id),
    FOREIGN KEY (inventor_id) REFERENCES inventors(inventor_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
) ENGINE=InnoDB;