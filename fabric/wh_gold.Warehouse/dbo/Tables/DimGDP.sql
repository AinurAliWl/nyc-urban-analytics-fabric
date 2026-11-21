CREATE TABLE [dbo].[DimGDP] (
    [country_code]   VARCHAR (3)     NOT NULL,
    [country_name]   VARCHAR (100)   NOT NULL,
    [indicator_code] VARCHAR (32)    NOT NULL,
    [gdp_year]       INT             NOT NULL,
    [gdp_usd]        DECIMAL (20, 2) NULL
);


GO