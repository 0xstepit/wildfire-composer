# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: wildfire-composer
#     language: python
#     name: wildfire-composer
# ---

# %% [markdown]
# # CEMS connection

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import duckdb

# %%
# In-memory db
con = duckdb.connect()

# %%
con.install_extension("httpfs")
con.load_extension("httpfs")

# %% [markdown]
# There are two API endpoints for two different services offered by the **Emergency Management Service**:
#
# - **Mapping API**: contains all the active and past mapping activations.
# - **Rapid Mapping API**: contains information about emergency mapping activations performed by the Copernicu Rapid Mapping management team. This is a subset of the activations exposed by the previous endpoint.

# %%
url_mapping = "https://mapping.emergency.copernicus.eu/activations/api/activations/"
url_rapidmapping = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations-info/"
url_extended = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/"

# %%
df_mapping = con.execute(f"SELECT * FROM read_json_auto('{url_mapping}')").df()
df_mapping

# %% [markdown]
# The `next` field returns the endpoint to hit with the paginated query applied for the next batch of data.

# %%
df_mapping["next"].item()

# %%
df_rapidmapping = con.execute(f"SELECT * FROM read_json_auto('{url_rapidmapping}')").df()
df_rapidmapping

# %%
df_extended = con.execute(f"SELECT * FROM read_json_auto('{url_extended}')").df()
df_extended

# %% [markdown]
# With DuckDB we can also unnest directly the `results` field:

# %%
df = con.execute(f"SELECT unnest(results) as 'Activation' FROM read_json_auto('{url_mapping}')").df()
df

# %%
df.iloc[7].to_dict()

# %%
code = "EMSR908"
url_cems = url_rapidmapping + f"?code={code}"
df_908 = con.execute(f"SELECT * FROM read_json_auto('{url_cems}')").df()

# %%
df_908["results"].to_dict()

# %%
code = "EMSR901"
url_cems = url_rapidmapping + f"?code={code}"
df_901 = con.execute(f"SELECT * FROM read_json_auto('{url_cems}')").df()

# %%
df_901["results"].to_dict()

# %%
code = "EMSR897"
url_cems = url_extended + f"?code={code}"
df_900 = con.execute(f"SELECT * FROM read_json_auto('{url_cems}')").df()

# %%
dict_900 = df_900["results"].to_dict()
dict_900

# %%
act = dict_900[0][0]
act

# %%
from shapely import from_wkt

# %%
type(from_wkt(act['extent']))

# %%
act["aois"][0]

# %%
act["aois"][0]["products"][1]

# %%
