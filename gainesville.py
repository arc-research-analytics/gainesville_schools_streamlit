import streamlit as st
from datetime import datetime
from PIL import Image
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import plotly.express as px
from millify import millify
from millify import prettify
# import leafmap.colormaps as cm
# from leafmap.common import hex_to_rgb
import jenkspy
from datetime import date
import numpy as np

# custo-myze vvvvvvvvvvvvvvvvvvvvvvvv
im = Image.open('content/logo.png')
st.set_page_config(page_title='School Map', layout="wide", page_icon=im)

do_custom_stuff = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        section.main > div:has(~ footer ) {
        padding-bottom: 5px;
        padding-right: 0px;
        }
        div.block-container{padding-top:1.5rem;}
        div[data-baseweb="select"] > div {
            background-color: #5A5A5A;
            color: #FFFFFF !important;
        }
        li>div {
            color:  #FFFFFF !important;
        }
       </style>
       """

st.markdown(do_custom_stuff, unsafe_allow_html=True)

custom_colors_dark = ['#ffffff','#a7b2b8','#70828c','#3c5461','#022b3a']

# convert the above hex list to RGB values
colors_dark_rgb = [tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) for h in custom_colors_dark]

# custo-myze ^^^^^^^^^^^^^^^^^^^^^^^^^

# Main section header
st.markdown("<h2><span style='color:#FFFFFF'>Gainesville City School Board Map</span></h2>", unsafe_allow_html=True)

# sidebar
map_view = st.sidebar.radio(
    'Map view:',
    ('Demographics only','Demographics + enrollment')
)
map_var = st.sidebar.selectbox(
    'Select demographic variable:',
    ('Current population',
     'Projected population',
     'Median household income',
     'Millennial population')
)

if map_view == 'Demographics + enrollment':
    school_var = st.sidebar.selectbox(
        'View student footprint for:',
        ('Gainesville High',
         'Gainesville Middle (East)',
         'Gainesville Middle (West)',
         'Enota Multiple Intelligences Academy'
     ))
    icon_layer = st.sidebar.checkbox('Show school location')
else:
    school_var = "Gainesville High"

school_var_dict = {
    'Gainesville High':'Gainesville_high',
    'Gainesville Middle (East)':'Gainesville_middle_E',
    'Gainesville Middle (West)':'Gainesville_middle_W',
    'Enota Multiple Intelligences Academy':'Enota'

}

school_tooltip_dict = {
    'Gainesville High':'Gainesville High',
    'Gainesville Middle (East)':'Gainesville Middle (E)',
    'Gainesville Middle (West)':'Gainesville Middle (W)',
    'Enota Multiple Intelligences Academy':'Enota'

}

basemap = st.sidebar.selectbox(
    'Select base map:',
    ('Light',
     'Dark',
     'Streets', 
     'Satellite'
     )
)

basemap_dict = {
    'Streets':'road',
    'Satellite':'satellite',
    'Light':'light',
    'Dark':'dark'
}

# the map
col1, col2, col3 = st.columns([4,1,0.2])

@st.cache_data
def load_data():

    gdf = gpd.read_file('Data/Geospatial/Gainesville_BG.gpkg')
    

    df = pd.read_csv('Data/Gainesville_test.csv', thousands=',')
    df['Block Group'] = df['Block Group'].astype(str)

    gdf_joined = gdf.merge(df, left_on = 'GEOID', right_on = 'Block Group')
    gdf_joined = gdf_joined.drop(columns=['STATEFP','COUNTYFP','TRACTCE','BLKGRPCE','NAMELSAD','MTFCC','FUNCSTAT','ALAND','AWATER','INTPTLAT','INTPTLON','Block Group'])

    gdf_joined = gdf_joined[[
        'geometry',
        'GEOID',
        '2022 Total Population',
        '2027 Total Population',
        '2022 Median Household Income',
        '2022 Millennial Pop',
        'Gainesville_high',
        'Gainesville_middle_E',
        'Gainesville_middle_W',
        'Enota'
        ]]

    gdf_joined['2022 Median Household Income'] = gdf_joined['2022 Median Household Income'].astype(str).str.replace('$','').str.replace(',','').astype(int)
    gdf_joined.to_file('testerChester.gpkg')
    # gdf_joined.drop(columns=['geometry'], inplace=True)
    # st.write(gdf_joined.columns)

    return gdf_joined

def school_map_2D():

    # create the tooltip label
    gdf_joined['tooltip_label'] = map_var

    # create the tooltip value
    map_var_dict = {
        'Current population':gdf_joined['2022 Total Population'],
        'Projected population':gdf_joined['2027 Total Population'],
        'Median household income':gdf_joined['2022 Median Household Income'],
        'Millennial population':gdf_joined['2022 Millennial Pop']
    }

    if map_var == 'Median household income':
        gdf_joined['tooltip_value'] = gdf_joined['2022 Median Household Income'].apply(lambda x: "${:,.0f}".format((x)))
    else:
        gdf_joined['tooltip_value'] = map_var_dict[map_var].apply(lambda x: "{:,.0f}".format((x)))

    # set choropleth color
    map_var_color = {
        'Current population':'Blues',
        'Projected population':'Blues',
        'Median household income':'Greens',
        'Millennial population':'Purples'
    }

    # color_brewer_colors = cm.get_palette(map_var_color[map_var], 5)
    # colors_rgb = [hex_to_rgb(c) for c in color_brewer_colors]

    colors_rgb = list(colors_dark_rgb)

    # ignore the first value, which is essentially white
    colors_rgb = colors_rgb[1:]

    # set choropleth column 
    gdf_joined['choro_color'] = pd.cut(
        map_var_dict[map_var],
        bins=jenkspy.jenks_breaks(map_var_dict[map_var], n_classes=4),
        labels=colors_rgb,
        include_lowest=True,
        duplicates='drop'
        )
   
    # create map intitial state
    initial_view_state = pdk.ViewState(
        latitude=34.29249106933631, 
        longitude= -83.82716252552814,
        zoom=11.5, 
        max_zoom=15, 
        min_zoom=10,
        pitch=0,
        bearing=0,
        height=650
    )

    geojson = pdk.Layer(
        "GeoJsonLayer",
        gdf_joined,
        pickable=True,
        autoHighlight=True,
        highlight_color = [255, 255, 255, 80],
        opacity=0.5,
        stroked=True,
        filled=True,
        wireframe=True,
        extruded=False,
        get_fill_color='choro_color',
        get_line_color=[0, 0, 0, 80],
        line_width_min_pixels=1,
    )

    tooltip = {
        "html": "{tooltip_label}: <b>{tooltip_value}</b>",
        "style": {
        "background": "rgba(211,211,211,0.7)", 
        "border-radius": "7px", 
        "border-style": "solid",
        "border-color":"#5A5A5A",
        "border-width": "1px",
        "color": "black", 
        "font-family": "Arial"
        },
        }


    r = pdk.Deck(
        layers=geojson,
        initial_view_state=initial_view_state,
        map_provider='mapbox',
        map_style=basemap_dict[basemap],
        tooltip=tooltip)

    # gdf_joined.drop(columns=['geometry'], inplace=True)

    return r

def school_map_3D():

    # define the height of the block group
    gdf_joined['height'] = gdf_joined[school_var_dict[school_var]]

    # define which school will appear in the popup
    gdf_joined['school'] = school_tooltip_dict[school_var]

    # define the demographic label of the tooltip
    gdf_joined['tooltip_label'] = map_var

    # create the tooltip value
    map_var_dict = {
        'Current population':gdf_joined['2022 Total Population'],
        'Projected population':gdf_joined['2027 Total Population'],
        'Median household income':gdf_joined['2022 Median Household Income'],
        'Millennial population':gdf_joined['2022 Millennial Pop']
    }

    if map_var == 'Median household income':
        gdf_joined['tooltip_value'] = gdf_joined['2022 Median Household Income'].apply(lambda x: "${:,.0f}".format((x)))
    else:
        gdf_joined['tooltip_value'] = map_var_dict[map_var].apply(lambda x: "{:,.0f}".format((x)))

    kpi_total = gdf_joined[school_var_dict[school_var]].sum()
    gdf_joined['percent_enrollment'] = gdf_joined[school_var_dict[school_var]] / kpi_total
    gdf_joined['percent_enrollment'] = gdf_joined['percent_enrollment'].astype(float).map("{:.1%}".format)


    # create choropleth color ramp
    map_var_color = {
        'Current population':'Blues',
        'Projected population':'Blues',
        'Median household income':'Greens',
        'Millennial population':'Purples'
    }

    # color_brewer_colors = cm.get_palette(map_var_color[map_var], 5)
    # colors_rgb = [hex_to_rgb(c) for c in color_brewer_colors]
    colors_rgb = list(colors_dark_rgb)

    # ignore the first value, which is essentially white
    colors_rgb = colors_rgb[1:]

    gdf_joined['choro_color'] = pd.cut(
            map_var_dict[map_var],
            bins=jenkspy.jenks_breaks(map_var_dict[map_var], n_classes=4),
            labels=colors_rgb,
            include_lowest=True,
            duplicates='drop'
            )
    
    # create map intitial state
    initial_view_state = pdk.ViewState(
        latitude=34.300005779915246,
        longitude=-83.82599193768385,  
        zoom=11, 
        max_zoom=15, 
        min_zoom=10,
        pitch=0,
        bearing=0,
        height=650
    )

    geojson = pdk.Layer(
        "GeoJsonLayer",
        gdf_joined,
        pickable=True,
        autoHighlight=True,
        highlight_color = [255, 255, 255, 80],
        opacity=0.5,
        stroked=True,
        filled=True,
        wireframe=False,
        extruded=True,
        get_elevation='height * 12',
        get_fill_color='choro_color',
        line_width_min_pixels=1,
    )

    # data to create school icons
    icon_data = {
        "url": "https://img.icons8.com/plasticine/200/000000/marker.png",
        "width": 128,
        "height":128,
        "anchorY": 128
    }

    data = pd.DataFrame.from_dict({
        'Gainesville High':[34.29960903520855, -83.84442966091056],
        'Gainesville Middle (East)':[34.31112668885826, -83.80665550041583],
        'Gainesville Middle (West)':[34.280978888226485, -83.86770878573842],
        'Enota Multiple Intelligences Academy':[34.32353081469683, -83.82289012405307]
        }, 
        orient='index',
        columns=['lat', 'lon'])
    data = data[data.index == school_var]

    data['icon_data']= None
    for i in data.index:
        data['icon_data'][i] = icon_data

    icons = pdk.Layer(
        type='IconLayer',
        data=data,
        get_icon='icon_data',
        get_size=4,
        pickable=False,
        size_scale=15,
        get_position=["lon", "lat"]
    )


    tooltip = {
        "html": "{tooltip_label}: <b>{tooltip_value}</b><br> \
            {school} enrollment: <b>{height}</b><br> \
            Percent of total enrollment: <b>{percent_enrollment}</b>",
        "style": {
        "background": "rgba(211,211,211,0.7)", 
        "border-radius": "7px", 
        "border-style": "solid",
        "border-color":"#5A5A5A",
        "border-width": "1px",
        "color": "black", 
        "font-family": "Arial"
        },
        }

    if icon_layer:
        r = pdk.Deck(
            layers=[icons, geojson],
            initial_view_state=initial_view_state,
            map_provider='mapbox',
            map_style=basemap_dict[basemap],
            tooltip=tooltip)
    else:
        r = pdk.Deck(
            layers=[geojson],
            initial_view_state=initial_view_state,
            map_provider='mapbox',
            map_style=basemap_dict[basemap],
            tooltip=tooltip)


    return r

gdf_joined = load_data()


kpi_total = prettify(gdf_joined[school_var_dict[school_var]].sum())

if map_view == 'Demographics only':
    # st.dataframe(load_data())
    col1.pydeck_chart(school_map_2D(), use_container_width=True)
    col1.markdown("<span style='color:#FFFFFF'>Note: Darker colors corresponds to greater numeric value of demographic variable.</span>", unsafe_allow_html=True)
else:
    col1.pydeck_chart(school_map_3D(), use_container_width=True)
    col1.info("Note: Shift + click to change map pitch & angle. Darker colors corresponds to greater numeric value of demographic variable; 'taller' regions correpsond to larger enrollment footprint.")



# style the KPI readoutVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
fontsize_label = 25
fontsize_value = 35
align = "center"
iconname = "fas fa-book-reader"
KPI_label = f"{school_tooltip_dict[school_var]} <br>Total Enrollment:"
lnk = '<link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.12.1/css/all.css" crossorigin="anonymous">'
i = kpi_total

htmlstr = f"""<p style='
                        color: #FFFFFF; 
                        font-size: {fontsize_label}px; 
                        text-align: {align};
                        border-radius: 7px; 
                        padding-left: 12px; 
                        padding-top: 18px; 
                        padding-bottom: 18px; 
                        line-height:35px;'>
                        {KPI_label}
                        <br><span style='font-size: {fontsize_value}px; 
                        margin-top: 10px;'>{i} <br> <i class='{""} fa-xs'></i></span></p>"""

if map_view == 'Demographics + enrollment':
    col2.markdown(lnk + htmlstr, unsafe_allow_html=True)
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    image = Image.open('content/logo.png')
    with col2:
        subcol1, subcol2, subcol3 = st.columns([1,1,1])
        subcol2.image(image, width=80)
else:
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    col2.text("")
    image = Image.open('content/logo.png')
    with col2:
        subcol1, subcol2, subcol3 = st.columns([1,1,1])
        subcol2.image(image, width=80)
# KPI readout^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

