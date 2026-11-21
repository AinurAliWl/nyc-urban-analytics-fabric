CREATE TABLE [dbo].[DimFX] (
    [date_key]           INT             NOT NULL,
    [base_currency]      VARCHAR (3)     NOT NULL,
    [quote_currency]     VARCHAR (3)     NOT NULL,
    [usd_per_eur]        DECIMAL (18, 8) NOT NULL,
    [rate_source_date]   DATE            NOT NULL,
    [is_carried_forward] BIT             NOT NULL
);


GO