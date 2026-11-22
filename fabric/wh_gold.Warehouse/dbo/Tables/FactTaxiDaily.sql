CREATE TABLE [dbo].[FactTaxiDaily] (
    [date_key]                  INT             NOT NULL,
    [pickup_location_id]        INT             NOT NULL,
    [trip_count]                BIGINT          NOT NULL,
    [total_amount_usd]          DECIMAL (28, 2) NULL,
    [amount_trip_count]         BIGINT          NOT NULL,
    [distance_sum_miles]        DECIMAL (28, 4) NULL,
    [valid_distance_trip_count] BIGINT          NOT NULL,
    [duration_sum_seconds]      BIGINT          NULL,
    [valid_duration_trip_count] BIGINT          NOT NULL,
    [fare_sum_usd]              DECIMAL (28, 2) NULL,
    [fare_trip_count]           BIGINT          NULL
);


GO