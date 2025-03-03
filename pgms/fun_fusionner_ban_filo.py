import geopandas as gpd
import pandas as pd


def intersect_ban_avec_carreaux(
    ban: pd.DataFrame, polygons_gdf: gpd.GeoDataFrame, polygon_id_col: str
) -> gpd.GeoDataFrame:
    """
    Réalise l'intersection entre un GeoDataFrame de points issu de la BAN et un GeoDataFrame de polygones
    (carreaux Filosofi). La fonction suppose que les coordonnées de la BAN sont dans le même
    système de projection que les coordonnées des polygônes.

    Cette fonction conserve uniquement les points qui se trouvent à l'intérieur des polygones.
    Elle s'assure également que les deux GeoDataFrames partagent le même système de coordonnées (CRS).
    Les colonnes retournées sont :
      - Pour les points de la BAN : x, y (coordonnées) et la géométrie.
      - Pour les polygones : la géométrie et la colonne identifiant les polygones.

    Args:
        ban (DataFrame): DataFrame contenant les points de la BAN, il suffit que les colonnes x et y soient présentes.
        polygons_gdf (GeoDataFrame): GeoDataFrame contenant les polygones avec une colonne "geometry".
        polygon_id_col (str): Nom de la colonne identifiant les polygones dans `polygons_gdf`.

    Returns:
        GeoDataFrame: Un GeoDataFrame contenant les points situés dans les polygones,
                      avec les colonnes x, y, geometry (points) et la colonne identifiant les polygones.
    """
    points_gdf = gpd.GeoDataFrame(
        ban[["x", "y"]], geometry=gpd.points_from_xy(ban["x"], ban["y"]), crs=polygons_gdf.crs
    )

    # Effectuer une jointure spatiale pour conserver uniquement les points dans les polygones
    result = gpd.sjoin(
        points_gdf[["x", "y", "geometry"]], polygons_gdf[[polygon_id_col, "geometry"]], how="inner", predicate="within"
    )

    # Conserver uniquement les colonnes nécessaires
    result = result[["x", "y", polygon_id_col, "geometry"]]

    return result
