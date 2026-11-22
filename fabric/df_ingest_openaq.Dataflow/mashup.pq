[DefaultOutputDestinationSettings = [DestinationDefinition = [Kind = "Reference", QueryName = "DefaultDestination", IsNewTarget = true], UpdateMethod = [Kind = "Replace"], DestinationTypeSettings = [Kind = "Table"]], StagingDefinition = [Kind = "FastCopy"]]
section Section1;
shared DefaultDestination = Lakehouse.Contents([EnableFolding = false]){[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data]{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data];
[BindToDefaultDestination = true]
shared openaq_daily_raw = let
    Source = Lakehouse.Contents(null),
    Workspace = Source{[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data],
    Bronze = Workspace{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data],
    Files = Bronze{[Id = "Files", ItemKind = "Folder"]}[Data],
    PM25Folder = Files{[Name = "openaq_pm25"]}[Content],

    Batches = {
        [LocationId = 384, SensorId = 673, Year = 2022],
        [LocationId = 626, SensorId = 1102, Year = 2022],
        [LocationId = 384, SensorId = 673, Year = 2024],
        [LocationId = 626, SensorId = 1102, Year = 2024],
        [LocationId = 631, SensorId = 1152, Year = 2024]
    },

    ReadBatch = (batch as record) as table =>
        let
            FileName = "openaq_pm25_" & Text.From(batch[SensorId]) & "_"
                & Text.From(batch[Year]) & "_jan_feb.json",
            File = PM25Folder{[Name = FileName]}[Content],
            Payload = Json.Document(File, TextEncoding.Utf8),
            FirstDay = #date(batch[Year], 1, 1),
            EndDay = #date(batch[Year], 3, 1),
            Rows = List.Transform(
                Payload[results],
                (reading as record) as record =>
                    let
                        Coverage = if reading[coverage]? is record
                            then reading[coverage]
                            else []
                    in
                        [
                            location_id = batch[LocationId],
                            sensor_id = batch[SensorId],
                            pollutant = reading[parameter][name],
                            unit = reading[parameter][units],
                            local_date = Date.FromText(
                                Text.Start(reading[period][datetimeFrom][local], 10),
                                [Format = "yyyy-MM-dd", Culture = "en-US"]
                            ),
                            daily_mean = reading[value]?,
                            observed_hours = Coverage[observedCount]?,
                            expected_hours = Coverage[expectedCount]?
                        ]
            ),
            Daily = Table.FromRecords(Rows),
            InPeriod = Table.SelectRows(
                Daily,
                each [local_date] >= FirstDay and [local_date] < EndDay
            )
        in
            InPeriod,

    Combined = Table.Combine(List.Transform(Batches, ReadBatch)),
    Typed = Table.TransformColumnTypes(
        Combined,
        {
            {"location_id", Int64.Type},
            {"sensor_id", Int64.Type},
            {"pollutant", type text},
            {"unit", type text},
            {"local_date", type date},
            {"daily_mean", type number},
            {"observed_hours", Int64.Type},
            {"expected_hours", Int64.Type}
        }
    )
in
    Typed;
