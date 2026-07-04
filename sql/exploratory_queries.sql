-- 1. Total Companies
SELECT COUNT(*) AS total_companies
FROM companies;

-- 2. Companies by Sector
SELECT sector,
       COUNT(*) AS companies
FROM companies
GROUP BY sector
ORDER BY companies DESC;

-- 3. Top 10 Companies by Market Cap
SELECT c.company_name,
       m.market_cap
FROM market_cap m
JOIN companies c
ON m.company_id = c.company_id
ORDER BY m.market_cap DESC
LIMIT 10;

-- 4. Latest Net Profit
SELECT c.company_name,
       p.fiscal_year,
       p.net_profit
FROM profitandloss p
JOIN companies c
ON p.company_id = c.company_id
WHERE p.fiscal_year = (
    SELECT MAX(fiscal_year)
    FROM profitandloss
);

-- 5. Average ROE
SELECT AVG(return_on_equity)
FROM financial_ratios;

-- 6. Companies with Highest Revenue
SELECT c.company_name,
       MAX(p.sales)
FROM profitandloss p
JOIN companies c
ON p.company_id=c.company_id
GROUP BY c.company_name
ORDER BY MAX(p.sales) DESC;

-- 7. Row Counts
SELECT 'companies', COUNT(*) FROM companies
UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow;
