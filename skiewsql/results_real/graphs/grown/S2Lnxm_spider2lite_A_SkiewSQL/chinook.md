# Skill graph — `chinook` (12 skills)

**Skill `invoice_line_album_mapping`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `invoice_line_id` |
| output columns | `invoice_line_id`, `invoice_id`, `customer_id`, `album_id`, `artist_id`, `unit_price`, `quantity`, `line_total` |
| source tables | `invoice_items`, `tracks`, `albums`, `artists`, `invoices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `artist_revenue_by_line`, `album_invoice_lines`, `artist_total_album_sales`, `customer_spend_per_artist` |
| validated_on | — |
| counter_examples | 0 |

_Map each invoice line to the album and artist it contributes to. For invoice lines that reference tracks, associate the track's album and that album's artist. For invoice lines that directly reference albums (if applicable), associate the album and its artist. Include the invoice, customer, unit price, quantity, and invoice line total._

```sql
SELECT
  invoice_items.InvoiceLineId AS invoice_line_id,
  invoice_items.InvoiceId AS invoice_id,
  invoices.CustomerId AS customer_id,
  albums.AlbumId AS album_id,
  artists.ArtistId AS artist_id,
  invoice_items.UnitPrice AS unit_price,
  invoice_items.Quantity AS quantity,
  (invoice_items.UnitPrice * invoice_items.Quantity) AS line_total
FROM invoice_items
LEFT JOIN tracks ON invoice_items.TrackId = tracks.TrackId
LEFT JOIN albums ON tracks.AlbumId = albums.AlbumId
LEFT JOIN artists ON albums.ArtistId = artists.ArtistId
LEFT JOIN invoices ON invoice_items.InvoiceId = invoices.InvoiceId
```

---

**Skill `artist_revenue_by_line`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `invoice_line_id` |
| output columns | `invoice_line_id`, `artist_id`, `line_total` |
| source tables | `invoice_items`, `tracks`, `albums`, `invoice_line_album_mapping` |
| depends_on (builds on) | `invoice_line_album_mapping` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Compute revenue contribution per artist by summing invoice line totals, keeping one row per invoice line mapped to the artist (this prepares for artist-level aggregation)._

```sql
SELECT
  invoice_line_id,
  artist_id,
  line_total
FROM invoice_line_album_mapping
```

---

**Skill `artist_total_revenue`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `ArtistId` |
| output columns | `artist_id`, `artist_revenue` |
| source tables | `artists`, `albums`, `tracks`, `invoice_items` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `customer_spend_on_top_artist` |
| validated_on | — |
| counter_examples | 0 |

_Aggregate total sales revenue for each artist by summing line totals across all invoice lines associated with that artist. One row per artist with their total revenue._

```sql
SELECT
  a.ArtistId AS artist_id,
  COALESCE(SUM(ii.UnitPrice * ii.Quantity), 0.0) AS artist_revenue
FROM artists a
LEFT JOIN albums al ON al.ArtistId = a.ArtistId
LEFT JOIN tracks t ON t.AlbumId = al.AlbumId
LEFT JOIN invoice_items ii ON ii.TrackId = t.TrackId
GROUP BY a.ArtistId
```

---

**Skill `customer_spend_on_top_artist`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `CustomerId`, `FirstName` |
| output columns | `customer_id`, `customer_first_name`, `customer_spend_on_top_artist` |
| source tables | `customers`, `invoices`, `invoice_items`, `tracks`, `albums`, `artists`, `artist_total_revenue` |
| depends_on (builds on) | `artist_total_revenue` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_For the artist identified as the best-selling (highest artist_revenue from artist_total_revenue), compute each customer's total spending on that artist's albums by summing line totals per customer restricted to that artist. One row per customer with their spend on the top artist. This relation will be filtered later to keep spends < 1.00._

```sql
SELECT
  c.CustomerId AS customer_id,
  c.FirstName AS customer_first_name,
  COALESCE(SUM(ii.UnitPrice * ii.Quantity), 0.0) AS customer_spend_on_top_artist,
  c.CustomerId AS _pk_customer_id
FROM customers c
JOIN invoices i ON i.CustomerId = c.CustomerId
JOIN invoice_items ii ON ii.InvoiceId = i.InvoiceId
JOIN tracks t ON t.TrackId = ii.TrackId
JOIN albums a ON a.AlbumId = t.AlbumId
JOIN artist_total_revenue atr_max ON 1=1
  -- will join to pick the single top artist by artist_revenue in consuming query via equality below
JOIN artists art ON art.ArtistId = a.ArtistId
WHERE a.ArtistId = atr_max.artist_id
GROUP BY c.CustomerId, c.FirstName
```

---

**Skill `album_invoice_lines`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `invoice_line_id` |
| output columns | `invoice_id`, `customer_id`, `album_id`, `artist_id`, `quantity`, `line_amount` |
| source tables | `invoice_line_album_mapping` |
| depends_on (builds on) | `invoice_line_album_mapping` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Invoice line items restricted to products that are albums, keeping the invoice, customer, artist (via album->artist), quantity and line amount (price * quantity or invoice line total). One row per invoice line for an album._

```sql
SELECT
  il.invoice_line_id AS invoice_line_id,
  il.invoice_id AS invoice_id,
  il.customer_id AS customer_id,
  il.album_id AS album_id,
  il.artist_id AS artist_id,
  il.quantity AS quantity,
  COALESCE(il.line_total, il.unit_price * il.quantity) AS line_amount
FROM invoice_line_album_mapping il
```

---

**Skill `artist_total_album_sales`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `ArtistId`, `Name` |
| output columns | `artist_id`, `artist_name`, `artist_total_sales` |
| source tables | `artists`, `invoice_line_album_mapping` |
| depends_on (builds on) | `invoice_line_album_mapping` |
| depended-on by (builds on this) | `top_bottom_artist_averages_and_difference` |
| validated_on | — |
| counter_examples | 0 |

_Total album sales per artist computed by summing line_amount across all album invoice lines. One row per artist with their total album sales._

```sql
SELECT
  a.ArtistId AS artist_id,
  a.Name AS artist_name,
  COALESCE(SUM(il.line_total), 0.0) AS artist_total_sales
FROM artists a
LEFT JOIN invoice_line_album_mapping il ON il.artist_id = a.ArtistId
GROUP BY
  a.ArtistId,
  a.Name
```

---

**Skill `customer_spend_per_artist`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `customer_id`, `artist_id` |
| output columns | `customer_id`, `artist_id`, `customer_artist_spent` |
| source tables | `invoice_line_album_mapping` |
| depends_on (builds on) | `invoice_line_album_mapping` |
| depended-on by (builds on this) | `top_bottom_artist_averages_and_difference` |
| validated_on | — |
| counter_examples | 0 |

_Per-customer total spend on albums for each artist, computed by summing line_amount across invoice lines for that customer and artist. One row per customer-artist combination._

```sql
SELECT
  ilam.customer_id AS customer_id,
  ilam.artist_id AS artist_id,
  SUM(ilam.line_total) AS customer_artist_spent
FROM invoice_line_album_mapping ilam
GROUP BY
  ilam.customer_id,
  ilam.artist_id
```

---

**Skill `top_bottom_artist_averages_and_difference`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `customer_id` |
| output columns | `top_artist_name`, `bottom_artist_name`, `customer_id`, `customer_spent_on_top_artist`, `customer_spent_on_bottom_artist`, `avg_spent_top_artist`, `avg_spent_bottom_artist`, `absolute_difference` |
| source tables | `artist_total_album_sales`, `customer_spend_per_artist` |
| depends_on (builds on) | `artist_total_album_sales`, `customer_spend_per_artist` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Identify the top-selling and bottom-selling artist names by artist_total_sales with alphabetical tie-breaker, join to customer_spend_per_artist to get each customer's spend on those two artists (zero if no row), compute avg spend among customers with spend>0 for each artist, and produce absolute difference between those two averages. One row per customer used only in intermediate join, final outputs include the two artist names, the two averages, and their absolute difference._

```sql
SELECT
  top_artist.artist_name AS top_artist_name,
  bottom_artist.artist_name AS bottom_artist_name,
  csa.customer_id AS customer_id,
  COALESCE(top_spend.customer_artist_spent, 0.0) AS customer_spent_on_top_artist,
  COALESCE(bottom_spend.customer_artist_spent, 0.0) AS customer_spent_on_bottom_artist,
  top_stats.avg_spent_top_artist AS avg_spent_top_artist,
  bottom_stats.avg_spent_bottom_artist AS avg_spent_bottom_artist,
  ABS((top_stats.avg_spent_top_artist) - (bottom_stats.avg_spent_bottom_artist)) AS absolute_difference
FROM
  -- determine top-selling artist(s) by artist_total_sales with alphabetical tiebreaker, take single top
  (SELECT artist_id, artist_name
   FROM artist_total_album_sales
   WHERE artist_total_sales = (
     SELECT MAX(artist_total_sales) FROM artist_total_album_sales
   )
   ORDER BY artist_name ASC
   LIMIT 1
  ) AS top_artist
  CROSS JOIN
  -- determine bottom-selling artist(s) by artist_total_sales with alphabetical tiebreaker, take single bottom
  (SELECT artist_id, artist_name
   FROM artist_total_album_sales
   WHERE artist_total_sales = (
     SELECT MIN(artist_total_sales) FROM artist_total_album_sales
   )
   ORDER BY artist_name ASC
   LIMIT 1
  ) AS bottom_artist
  -- start from all customers who appear in customer_spend_per_artist (one row per customer used in intermediate join)
  JOIN (
    SELECT DISTINCT customer_id FROM customer_spend_per_artist
  ) AS csa ON 1=1
  -- left join each customer's spend on the top artist (zero if no row)
  LEFT JOIN customer_spend_per_artist AS top_spend
    ON top_spend.customer_id = csa.customer_id AND top_spend.artist_id = top_artist.artist_id
  -- left join each customer's spend on the bottom artist (zero if no row)
  LEFT JOIN customer_spend_per_artist AS bottom_spend
    ON bottom_spend.customer_id = csa.customer_id AND bottom_spend.artist_id = bottom_artist.artist_id
  -- compute average spend among customers with spend>0 for top artist
  LEFT JOIN (
    SELECT
      NULL AS marker,
      AVG(customer_artist_spent) AS avg_spent_top_artist
    FROM customer_spend_per_artist
    WHERE artist_id = (SELECT artist_id FROM artist_total_album_sales WHERE artist_total_sales = (SELECT MAX(artist_total_sales) FROM artist_total_album_sales) ORDER BY artist_name ASC LIMIT 1)
      AND customer_artist_spent > 0
  ) AS top_stats ON 1=1
  -- compute average spend among customers with spend>0 for bottom artist
  LEFT JOIN (
    SELECT
      NULL AS marker,
      AVG(customer_artist_spent) AS avg_spent_bottom_artist
    FROM customer_spend_per_artist
    WHERE artist_id = (SELECT artist_id FROM artist_total_album_sales WHERE artist_total_sales = (SELECT MIN(artist_total_sales) FROM artist_total_album_sales) ORDER BY artist_name ASC LIMIT 1)
      AND customer_artist_spent > 0
  ) AS bottom_stats ON 1=1
```

---

**Skill `sales_transactions`** — category `SEL`

| field | value |
|---|---|
| grain (one row per) | `transaction_id` |
| output columns | `transaction_id`, `customer_id`, `country`, `sale_value` |
| source tables | `invoices` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_All individual sales transactions with the transaction value and the customer-country association (one row per transaction). This filters/normalizes raw sales events into a cohort of sale records with a numeric sale_value and a customer_id and country identifier available._

```sql
SELECT
  invoices.InvoiceId AS transaction_id,
  invoices.CustomerId AS customer_id,
  invoices.BillingCountry AS country,
  invoices.Total AS sale_value
FROM invoices
```

---

**Skill `customers_per_country`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `Country` |
| output columns | `country`, `distinct_customer_count` |
| source tables | `customers` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `country_customer_sales_for_median` |
| validated_on | — |
| counter_examples | 0 |

_Count of distinct customers in each country (one row per country). This computes how many customers belong to each country to later filter countries with more than 4 customers._

```sql
SELECT
  Country AS country,
  COUNT(DISTINCT CustomerId) AS distinct_customer_count
FROM customers
GROUP BY Country
```

---

**Skill `total_sales_per_country_customer`** — category `AGG`

| field | value |
|---|---|
| grain (one row per) | `BillingCountry`, `CustomerId` |
| output columns | `country`, `customer_id`, `customer_total_sales` |
| source tables | `invoices`, `customers` |
| depends_on (builds on) | — (reads base tables directly) |
| depended-on by (builds on this) | `country_customer_sales_for_median` |
| validated_on | — |
| counter_examples | 0 |

_Total sales per customer within each country (one row per customer within a country). This aggregates sales_transactions to compute each customer's total sales and preserves customer and country keys._

```sql
SELECT
  invoices.BillingCountry AS country,
  customers.CustomerId AS customer_id,
  SUM(invoices.Total) AS customer_total_sales
FROM invoices
JOIN customers ON customers.CustomerId = invoices.CustomerId
GROUP BY invoices.BillingCountry, customers.CustomerId
```

---

**Skill `country_customer_sales_for_median`** — category `JOIN`

| field | value |
|---|---|
| grain (one row per) | `country`, `customer_id` |
| output columns | `country`, `customer_id`, `customer_total_sales` |
| source tables | `total_sales_per_country_customer`, `customers_per_country` |
| depends_on (builds on) | `total_sales_per_country_customer`, `customers_per_country` |
| depended-on by (builds on this) | — |
| validated_on | — |
| counter_examples | 0 |

_Join customer-level totals with country customer counts and filter to countries having more than 4 customers. Yields the set of customer_total_sales values used to compute each country's distribution (one row per customer within qualifying countries). The final median computation across countries will operate on these per-country customer totals._

```sql
SELECT
  t.customer_id AS customer_id,
  t.country AS country,
  t.customer_total_sales AS customer_total_sales,
  c.distinct_customer_count AS distinct_customer_count
FROM total_sales_per_country_customer t
JOIN customers_per_country c
  ON t.country = c.country
WHERE c.distinct_customer_count > 4
```

---
