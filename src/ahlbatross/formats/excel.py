"""
contains excel export logic.
"""

from pathlib import Path

import pandas as pd
from pandas import DataFrame

from ahlbatross.logger import logger


# pylint:disable=too-many-branches, too-many-locals, too-many-statements
def export_to_excel(df: DataFrame, output_path_xlsx: str) -> None:
    """
    exports the merged dataframe to .xlsx with highlighted differences.
    """
    sheet_name = Path(output_path_xlsx).stem  # excel sheet name = <pruefid>

    # add column for indexing through all rows.
    df = df.reset_index()
    df["index"] = df["index"] + 1
    df = df.rename(columns={"index": "#"})

    changed_entries_series = df["changed_entries"] if "changed_entries" in df.columns else pd.Series([""] * len(df))

    # remove duplicate columns that index through the rows.
    df_filtered = df[[col for col in df.columns if not col.startswith("Unnamed:") and col != "changed_entries"]]

    with pd.ExcelWriter(output_path_xlsx, engine="xlsxwriter") as writer:
        df_filtered.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # sticky table header
        worksheet.freeze_panes(1, 0)
        if not df_filtered.empty:
            table_options = {
                "style": "None",
                "columns": [{"header": col} for col in df_filtered.columns],
            }
            worksheet.add_table(0, 0, len(df_filtered), len(df_filtered.columns) - 1, table_options)

        # base formatting.
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D9D9D9", "border": 1, "align": "center", "text_wrap": True}
        )
        base_format = workbook.add_format({"border": 1, "text_wrap": True})

        # formatting highlighted/changed cells.
        diff_formats = {
            "NEU": workbook.add_format({"bg_color": "#C6EFCE", "border": 1, "text_wrap": True}),
            "ENTFÄLLT": workbook.add_format({"bg_color": "#FFC7CE", "border": 1, "text_wrap": True}),
            "ÄNDERUNG": workbook.add_format({"bg_color": "#F5DC98", "border": 1, "text_wrap": True}),
            "segmentname_changed": workbook.add_format({"bg_color": "#D9D9D9", "border": 1, "text_wrap": True}),
            "": workbook.add_format({"border": 1, "text_wrap": True}),
        }

        # applies bold font to `Segmentname` entries every time the value changes.
        highlight_segmentname = {
            "NEU": workbook.add_format({"bold": True, "bg_color": "#C6EFCE", "border": 1, "text_wrap": True}),
            "ENTFÄLLT": workbook.add_format({"bold": True, "bg_color": "#FFC7CE", "border": 1, "text_wrap": True}),
            "ÄNDERUNG": workbook.add_format({"bold": True, "bg_color": "#F5DC98", "border": 1, "text_wrap": True}),
            "segmentname_changed": workbook.add_format(
                {"bold": True, "bg_color": "#D9D9D9", "border": 1, "text_wrap": True}
            ),
            "": workbook.add_format({"bold": True, "border": 1, "text_wrap": True}),
        }

        # formatting 'Änderung' column.
        diff_text_formats = {
            "NEU": workbook.add_format(
                {
                    "bold": True,
                    "color": "#7AAB8A",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "ENTFÄLLT": workbook.add_format(
                {
                    "bold": True,
                    "color": "#E94C74",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "ÄNDERUNG": workbook.add_format(
                {
                    "bold": True,
                    "color": "#B8860B",
                    "border": 1,
                    "bg_color": "#D9D9D9",
                    "align": "center",
                    "text_wrap": True,
                }
            ),
            "": workbook.add_format({"border": 1, "bg_color": "#D9D9D9", "align": "center", "text_wrap": True}),
        }

        for col_num, value in enumerate(df_filtered.columns.values):
            worksheet.write(0, col_num, value, header_format)

        previous_formatversion = None
        subsequent_formatversion = None
        for col in df_filtered.columns:
            if col.startswith("Segmentname_"):
                suffix = col.split("Segmentname_")[1]
                if previous_formatversion is None:
                    previous_formatversion = suffix
                else:
                    subsequent_formatversion = suffix
                    break

        diff_idx = df_filtered.columns.get_loc("Änderung")
        previous_segmentname = None

        for row_num, row in enumerate(df_filtered.itertuples(index=False), start=1):
            row_data = list(row)
            diff_value = str(row_data[diff_idx])

            changed_entries = []
            if diff_value == "ÄNDERUNG":
                changed_entries_value = str(changed_entries_series.iloc[row_num - 1])
                if changed_entries_value != "nan":
                    changed_entries = changed_entries_value.split("|")

            # check if current `Segmentname` changed.
            current_segmentname = None
            for col_name in df_filtered.columns:
                if col_name.startswith("Segmentname_"):
                    idx = df_filtered.columns.get_loc(col_name)
                    value = str(row_data[idx])
                    if value:
                        current_segmentname = value
                        break

            is_new_segment = current_segmentname and current_segmentname != previous_segmentname
            previous_segmentname = current_segmentname

            for col_num, (value, col_name) in enumerate(zip(row_data, df_filtered.columns)):
                value = str(value) if value != "" else ""

                is_segmentname = col_name.startswith("Segmentname_")

                if col_name == "Änderung":
                    worksheet.write(row_num, col_num, value, diff_text_formats[diff_value])
                elif (
                    diff_value == "ENTFÄLLT"
                    and previous_formatversion is not None
                    and isinstance(col_name, str)
                    and col_name.endswith(previous_formatversion)
                ):
                    format_to_use = (
                        highlight_segmentname["ENTFÄLLT"]
                        if is_segmentname and is_new_segment
                        else diff_formats["ENTFÄLLT"]
                    )
                    worksheet.write(row_num, col_num, value, format_to_use)
                elif (
                    diff_value == "NEU"
                    and subsequent_formatversion is not None
                    and isinstance(col_name, str)
                    and col_name.endswith(subsequent_formatversion)
                ):
                    format_to_use = (
                        highlight_segmentname["NEU"] if is_segmentname and is_new_segment else diff_formats["NEU"]
                    )
                    worksheet.write(row_num, col_num, value, format_to_use)
                elif diff_value == "ÄNDERUNG":
                    if col_name in changed_entries:
                        format_to_use = (
                            highlight_segmentname["ÄNDERUNG"]
                            if is_segmentname and is_new_segment
                            else diff_formats["ÄNDERUNG"]
                        )
                    else:
                        format_to_use = (
                            highlight_segmentname["segmentname_changed"]
                            if is_segmentname and is_new_segment
                            else (diff_formats["segmentname_changed"] if is_new_segment else base_format)
                        )
                    worksheet.write(row_num, col_num, value, format_to_use)
                else:
                    # only apply grey background if the row is not affected by NEU/ENTFÄLLT highlighting
                    if is_new_segment and diff_value == "":
                        format_to_use = (
                            highlight_segmentname["segmentname_changed"]
                            if is_segmentname
                            else diff_formats["segmentname_changed"]
                        )
                        worksheet.write(row_num, col_num, value, format_to_use)
                    else:
                        worksheet.write(row_num, col_num, value, base_format)

        column_widths = {
            "#": 25,
            "Segmentname_": 175,
            "Segmentgruppe_": 100,
            "Segment_": 100,
            "Datenelement_": 100,
            "Segment ID_": 100,
            "Code_": 100,
            "Qualifier_": 100,
            "Beschreibung_": 150,
            "Bedingungsausdruck_": 100,
            "Bedingung_": 150,
        }

        for col_num, col_name in enumerate(df_filtered.columns):
            width_px = next(
                (width for prefix, width in column_widths.items() if col_name.startswith(prefix)), 150
            )  # default = 150 px
            excel_width = width_px / 7
            worksheet.set_column(col_num, col_num, excel_width)

        logger.info("✅ Successfully exported XLSX file to: %s", {output_path_xlsx})
