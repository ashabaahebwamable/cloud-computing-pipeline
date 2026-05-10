 Q1: Top Inventors
SELECT i.name, COUNT(r.patent_id) as patent_count
FROM inventors i
JOIN relationships r ON i.inventor_id = r.inventor_id
GROUP BY i.inventor_id, i.name
ORDER BY patent_count DESC
LIMIT 10;

Q2: Top Companies
SELECT c.name, COUNT(r.patent_id) as patent_count
FROM companies c
JOIN relationships r ON c.company_id = r.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC
LIMIT 10;

 Q3: Countries
SELECT i.country, COUNT(DISTINCT r.patent_id) as patent_count
FROM inventors i
JOIN relationships r ON i.inventor_id = r.inventor_id
WHERE i.country IS NOT NULL
GROUP BY i.country
ORDER BY patent_count DESC
LIMIT 10;

 Q4: Trends Over Time
SELECT year, COUNT(*) as patent_count
FROM patents
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year;

Q5: JOIN Query
SELECT p.patent_id, p.title, i.name as inventor_name, c.name as company_name
FROM patents p
LEFT JOIN relationships r ON p.patent_id = r.patent_id
LEFT JOIN inventors i ON r.inventor_id = i.inventor_id
LEFT JOIN companies c ON r.company_id = c.company_id
LIMIT 20;

Q6: CTE Query
WITH inventor_counts AS (
    SELECT inventor_id, COUNT(patent_id) as patent_count
    FROM relationships
    GROUP BY inventor_id
)
SELECT i.name, ic.patent_count
FROM inventors i
JOIN inventor_counts ic ON i.inventor_id = ic.inventor_id
ORDER BY ic.patent_count DESC
LIMIT 10;

Q7: Ranking Query
SELECT name, patent_count,
       RANK() OVER (ORDER BY patent_count DESC) as rank
FROM (
    SELECT i.name, COUNT(r.patent_id) as patent_count
    FROM inventors i
    JOIN relationships r ON i.inventor_id = r.inventor_id
    GROUP BY i.inventor_id, i.name
) sub
ORDER BY rank
LIMIT 10;