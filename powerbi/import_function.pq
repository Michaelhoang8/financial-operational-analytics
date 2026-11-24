// Create a blank query named LoadModelCsv, then paste this function.
// Create a Text parameter named DataFolder with the absolute data/model folder path.
(TableName as text) as table =>
let
    Source = Csv.Document(File.Contents(DataFolder & "/" & TableName & ".csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TextColumns = {"Branch", "Account", "Category", "SKU", "YearMonth"},
    DateColumns = {"Date", "PromisedDate", "ShippedDate"},
    Types = List.Transform(Table.ColumnNames(Headers), each {_, if List.Contains(DateColumns, _) then type date else if List.Contains(TextColumns, _) then type text else if _ = "StandardCost" then Currency.Type else Int64.Type}),
    Typed = Table.TransformColumnTypes(Headers, Types, "en-CA"),
    CleanText = Table.TransformColumns(Typed, List.Transform(List.Intersect({Table.ColumnNames(Typed),TextColumns}), each {_, Text.Trim, type text}))
in
    CleanText
