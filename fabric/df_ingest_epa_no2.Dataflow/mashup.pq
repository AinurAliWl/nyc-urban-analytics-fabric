[StagingDefinition = [Kind = "FastCopy"]]
section Section1;
[DataDestinations = {[Definition = [Kind = "Reference", QueryName = "epa_no2_daily_raw_DataDestination", IsNewTarget = true], Settings = [Kind = "Automatic", TypeSettings = [Kind = "Table"]]]}]
shared epa_no2_daily_raw = let
    Source = Lakehouse.Contents(null),
    Workspace = Source{[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data],
    Bronze = Workspace{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data],
    Files = Bronze{[Id = "Files", ItemKind = "Folder"]}[Data],
    EpaFolder = Files{[Name = "epa_no2"]}[Content],

    SourceFiles = {
        "epa_no2_nyc_2022_jan_feb.csv",
        "epa_no2_nyc_2024_jan_feb.csv"
    },

    ReadCsv = (fileName as text) as table =>
        let
            File = EpaFolder{[Name = fileName]}[Content],
            Csv = Csv.Document(
                File,
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Headers = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
            WithSource = Table.AddColumn(Headers, "source_file", each fileName, type text)
        in
            WithSource,

    Combined = Table.Combine(List.Transform(SourceFiles, ReadCsv)),
    Renamed = Table.TransformColumnNames(
        Combined,
        each Text.Lower(Text.Replace(Text.Replace(_, "1st ", "First "), " ", "_"))
    ),
    AsText = Table.TransformColumnTypes(
        Renamed,
        List.Transform(Table.ColumnNames(Renamed), each {_, type text})
    )
in
    AsText;
shared epa_no2_daily_raw_DataDestination = let
  Pattern = Lakehouse.Contents([HierarchicalNavigation = true, EnableVorder = true, OutputMetadataRefresh = true, CreateNavigationProperties = false, EnableFolding = false]),
  Navigation_1 = Pattern{[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data],
  Navigation_2 = Navigation_1{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data],
  Navigation_3 = Navigation_2{[Id = "dbo", ItemKind = "Schema"]}[Data],
  TableNavigation = Navigation_3{[Id = "epa_no2_daily_raw", ItemKind = "Table"]}?[Data]?
in
  TableNavigation;
