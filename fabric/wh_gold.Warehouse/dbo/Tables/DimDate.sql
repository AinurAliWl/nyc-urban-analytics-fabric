CREATE TABLE [dbo].[DimDate] (
    [date_key]         INT  NOT NULL,
    [calendar_date]    DATE NOT NULL,
    [calendar_year]    INT  NOT NULL,
    [calendar_quarter] INT  NOT NULL,
    [calendar_month]   INT  NOT NULL,
    [day_of_month]     INT  NOT NULL,
    [is_weekend]       BIT  NOT NULL
);


GO