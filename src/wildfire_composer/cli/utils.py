from csv import Error

from rich.table import Table

from wildfire_composer.raster import CompositeKind


def wildfire_list_to_table(rows) -> Table:
    table = Table(title="CEMS wildfire activations")
    table.add_column("Code", style="bold cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Region")
    table.add_column("Acrivated", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    for row in rows:
        (code, name, countries, activation_time, closed, _, _) = row
        table.add_row(
            code,
            name,
            countries,
            activation_time,
            "[blue] closed" if closed else "[yellow] open",
        )

    return table


def get_kind_by_str(string) -> CompositeKind:
    if string == "false-color":
        return CompositeKind.FALSE
    elif string == "rgb":
        return CompositeKind.RGB
    # elif string == "dnbr":
    #     return CompositeKind.DNBR
    # if string == "all":
    #     return CompositeKind.ALL
    else:
        raise Error(f"Image kind {string} is not known")
