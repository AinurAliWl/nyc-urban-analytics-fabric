[DefaultOutputDestinationSettings = [DestinationDefinition = [Kind = "Reference", QueryName = "DefaultDestination", IsNewTarget = true], UpdateMethod = [Kind = "Replace"], DestinationTypeSettings = [Kind = "Table"]], StagingDefinition = [Kind = "FastCopy"]]
section Section1;
shared DefaultDestination = Lakehouse.Contents([EnableFolding = false]){[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data]{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data];
[BindToDefaultDestination = true]
shared openaq_daily_raw = let
    Source = Lakehouse.Contents(null),
    Workspace = Source{[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data],
    Bronze = Workspace{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data],
    Files = Bronze{[Id = "Files", ItemKind = "Folder"]}[Data],
    OpenAQFolder = Files{[Name = "openaq"]}[Content],
    File = OpenAQFolder{[Name = "openaq_ccny_673_2024_01_02.json"]}[Content],
    Payload = Json.Document(File, TextEncoding.Utf8),

    Rows = List.Transform(Payload[results], (row) => [
        location_id = 384,
        sensor_id = 673,
        pollutant = row[parameter][name],
        unit = row[parameter][units],
        local_date = Date.FromText(
            Text.Start(row[period][datetimeFrom][local], 10),
            [Format = "yyyy-MM-dd"]
        ),
        daily_mean = row[value],
        observed_hours = row[coverage][observedCount],
        expected_hours = row[coverage][expectedCount]
    ]),

    Daily = Table.FromRecords(Rows, type table [
        location_id = number,
        sensor_id = number,
        pollutant = text,
        unit = text,
        local_date = date,
        daily_mean = nullable number,
        observed_hours = nullable number,
        expected_hours = nullable number
    ]),

    InPeriod = Table.SelectRows(
        Daily,
        each [local_date] >= #date(2024, 1, 1)
          and [local_date] < #date(2024, 3, 1)
    )
in
    InPeriod;
