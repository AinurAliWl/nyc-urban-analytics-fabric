[DefaultOutputDestinationSettings = [DestinationDefinition = [Kind = "Reference", QueryName = "DefaultDestination", IsNewTarget = true], UpdateMethod = [Kind = "Replace"], DestinationTypeSettings = [Kind = "Table"]], StagingDefinition = [Kind = "FastCopy"]]
section Section1;
shared DefaultDestination = Lakehouse.Contents([EnableFolding = false]){[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data]{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data];
[BindToDefaultDestination = true]
shared worldbank_gdp_raw = let
    Response = Json.Document(
        Web.Contents(
            "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD",
            [Query = [format = "json", date = "2000:2024", per_page = "100"]]
        )
    ),
    Records = Table.FromRecords(Response{1}),
    Selected = Table.SelectColumns(
        Records,
        {"countryiso3code", "country", "indicator", "date", "value"}
    ),
    Country = Table.ExpandRecordColumn(
        Selected, "country", {"value"}, {"country_name"}
    ),
    Indicator = Table.ExpandRecordColumn(
        Country, "indicator", {"id"}, {"indicator_code"}
    ),
    Renamed = Table.RenameColumns(
        Indicator,
        {
            {"countryiso3code", "country_code"},
            {"date", "gdp_year"},
            {"value", "gdp_usd"}
        }
    ),
    Typed = Table.TransformColumnTypes(
        Renamed,
        {{"gdp_year", Int64.Type}, {"gdp_usd", type number}}
    )
in
    Typed;
