[DefaultOutputDestinationSettings = [DestinationDefinition = [Kind = "Reference", QueryName = "DefaultDestination", IsNewTarget = true], UpdateMethod = [Kind = "Replace"], DestinationTypeSettings = [Kind = "Table"]], StagingDefinition = [Kind = "FastCopy"]]
section Section1;
shared DefaultDestination = Lakehouse.Contents([EnableFolding = false]){[workspaceId = "ff9401b1-9897-44bb-a371-52cdaf97b9b3"]}[Data]{[lakehouseId = "3f4301b6-a76f-414c-93e6-ce42e8b7d5b0"]}[Data];
[BindToDefaultDestination = true]
shared taxi_zones_raw = let
    Response = Web.Contents(
        "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
    ),
    Csv = Csv.Document(Response, [Delimiter = ",", Encoding = 65001]),
    Headers = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Headers,
        {
            {"LocationID", Int64.Type},
            {"Borough", type text},
            {"Zone", type text},
            {"service_zone", type text}
        }
    )
in
    Typed;
