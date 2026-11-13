import SwiftUI

/// Read-only native projection. Stacked column/value pairs preserve relationships
/// without a horizontal scroll lane or fixed text heights at accessibility sizes.
struct ScoutGenUITableView: View {
    let table: ScoutGenUITable
    var body: some View {
        VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
            if !table.title.isEmpty { Text(table.title).font(.headline).accessibilityAddTraits(.isHeader) }
            if table.columns.isEmpty || table.rows.isEmpty {
                Text("No tabular data.").font(.subheadline).foregroundStyle(.secondary)
            } else {
                ForEach(Array(table.rows.enumerated()), id: \.offset) { index, row in
                    VStack(alignment: .leading, spacing: ScoutVisualStyle.inset) {
                        ForEach(Array(table.columns.enumerated()), id: \.offset) { column, label in
                            VStack(alignment: .leading) {
                                Text(label).font(.caption).foregroundStyle(.secondary)
                                Text(row[column]).font(.body).fixedSize(horizontal: false, vertical: true)
                            }
                            .accessibilityElement(children: .combine)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    if index < table.rows.count - 1 { Divider() }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .modifier(ScoutPanel(secondary: true))
    }
}
