[DefaultOutputDestinationSettings = [DestinationDefinition = [Kind = "Reference", QueryName = "DefaultDestination", IsNewTarget = true], UpdateMethod = [Kind = "Replace"], DestinationTypeSettings = [Kind = "Table"]], StagingDefinition = [Kind = "FastCopy"]]
section Section1;
shared DefaultDestination = Lakehouse.Contents([EnableFolding = false]){[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data]{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data];
[BindToDefaultDestination = true]
shared ecb_fx_daily_raw = let
    Response = Web.Contents(
        "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A",
        [
            Query = [
                startPeriod = "2021-12-31",
                endPeriod = "2024-02-29",
                format = "csvdata"
            ]
        ]
    ),
    Csv = Csv.Document(Response, [Delimiter = ",", Encoding = 65001]),
    Headers = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
    Selected = Table.SelectColumns(
        Headers,
        {"TIME_PERIOD", "CURRENCY_DENOM", "CURRENCY", "OBS_VALUE"}
    ),
    Renamed = Table.RenameColumns(
        Selected,
        {
            {"TIME_PERIOD", "fx_date"},
            {"CURRENCY_DENOM", "base_currency"},
            {"CURRENCY", "quote_currency"},
            {"OBS_VALUE", "usd_per_eur"}
        }
    ),
    Typed = Table.TransformColumnTypes(
        Renamed,
        {
            {"fx_date", type date},
            {"base_currency", type text},
            {"quote_currency", type text},
            {"usd_per_eur", type number}
        },
        "en-US"
    ),
    Sorted = Table.Sort(Typed, {{"fx_date", Order.Ascending}})
in
    Sorted;
