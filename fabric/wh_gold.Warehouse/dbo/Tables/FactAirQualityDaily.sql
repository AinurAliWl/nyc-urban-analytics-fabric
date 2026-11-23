CREATE TABLE [dbo].[FactAirQualityDaily] (
    [date_key]               INT           NOT NULL,
    [location_id]            BIGINT        NOT NULL,
    [sensor_id]              BIGINT        NOT NULL,
    [pollutant]              VARCHAR (32)  NOT NULL,
    [unit]                   VARCHAR (32)  NOT NULL,
    [daily_mean]             FLOAT (53)    NULL,
    [observed_hours]         INT           NULL,
    [expected_hours]         INT           NULL,
    [coverage_ratio]         FLOAT (53)    NULL,
    [has_invalid_daily_mean] BIT           NOT NULL,
    [source_system]          VARCHAR (20)  NULL,
    [sensor_key]             VARCHAR (80)  NULL,
    [station_name]           VARCHAR (150) NULL
);


GO