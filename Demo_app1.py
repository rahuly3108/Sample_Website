#!/usr/bin/env python
# coding: utf-8

# In[1]:


import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import base64
import io
import dash_table
import plotly.express as px
from datetime import datetime
from urllib.parse import quote
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# Initialize the Dash app with suppress_callback_exceptions=True
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Define the layout of the page without the "Select Variable to Get the Summary Stats" section
initial_layout = html.Div([
    html.H1("Motor Insurance Analysis", style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.Button('Import Data')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'solid',
            'borderRadius': '12px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload'),
    dcc.Store(id='data-store')  # Add the dcc.Store component
])

# Set the layout of the Dash application
app.layout = initial_layout

# Callback to update the layout once the data is uploaded
@app.callback(Output('output-data-upload', 'children'),
              [Input('upload-data', 'contents')],
              prevent_initial_call=True)
def update_layout(contents):
    if contents is None:
        raise dash.exceptions.PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in content_type:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in content_type:
            # Assume that the user uploaded an Excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        return html.Div([
            'There was an error processing this file.'
        ])

    # Once the data is uploaded, return the layout with the "Select Variable to Get the Summary Stats" section
    return html.Div([
        html.H5('File uploaded successfully!'),
        html.H6(f'Number of rows: {len(df)}'),
        dash_table.DataTable(
            id='date-range-table',
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i, 'editable': True} for i in df.columns],
            page_size=10,
            style_table={'margin': 'auto', 'border': '2px solid black'},
            style_cell={'textAlign': 'center', 'padding': '8px'},
            style_header={'textAlign': 'center'}
        ),
        dcc.Store(id='data-store', data=df.to_csv(index=False)),  # Store dataframe as CSV string
        html.H2("Select Variable to Get the Summary Stats", style={'textAlign': 'center'}),
        dcc.RadioItems(
            id='radio-select',
            options=[{'label': col, 'value': col} for col in df.columns],
            value=df.columns[0],  # Select the first option by default
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}  # Display radio buttons horizontally
        ),
        dcc.Tabs(id='tabs', value='box-plot', children=[
            dcc.Tab(label='Box Plot', value='box-plot'),
            dcc.Tab(label='Statistics Table', value='stats-table'),
            dcc.Tab(label='Pie Chart', value='pie-chart'),
            dcc.Tab(label='Correlation Matrix', value='corr-matrix'),  # Add tab for correlation matrix
            dcc.Tab(label='Date Range Analysis', value='date-range-analysis')  # New tab for date range analysis
        ]),
        html.Div(id='tab-content')
    ])

# Callback to update the content of the selected tab
@app.callback(Output('tab-content', 'children'),
              [Input('tabs', 'value'),
               Input('radio-select', 'value'),
               Input('data-store', 'data')])
def update_tab_content(selected_tab, selected_variable, data):
    if not selected_variable or data is None:
        return None
    
    df = pd.read_csv(io.StringIO(data))  # Convert CSV string to DataFrame
    
    if selected_tab == 'box-plot':
        fig = px.box(df, y=selected_variable)
        fig.update_layout(title='Box Plot', xaxis_title='Variables', yaxis_title='Values')
        graph = dcc.Graph(figure=fig)
    elif selected_tab == 'stats-table':
        stats_table = df[selected_variable].describe().reset_index().round(2)
        stats_table.columns = ['Statistic', 'Value']
        graph = dash_table.DataTable(
            id='statistics-table',  # Add id to the statistics table
            data=stats_table.to_dict('records'),
            columns=[{'name': col, 'id': col} for col in stats_table.columns],
            style_data={'whiteSpace': 'normal', 'height': 'auto', 'textAlign': 'center'},
            style_cell={'padding': '8px'},
            style_header={'textAlign': 'center'}
        )
    elif selected_tab == 'pie-chart':
        fig = px.pie(df, names=df[selected_variable], title='Distribution of ' + selected_variable)
        graph = dcc.Graph(figure=fig)
    elif selected_tab == 'corr-matrix':
        return generate_corr_matrix(df)
    elif selected_tab == 'date-range-analysis':  # New tab for date range analysis
        if 'Date' not in df.columns:
            return html.Div("Error: 'Date' column not found in the uploaded data.")
        return html.Div([
            html.H2("Select Date Range", style={'textAlign': 'center'}),
            dcc.DatePickerRange(
                id='date-range-picker',
                start_date=df['Date'].min(),
                end_date=df['Date'].max(),
                min_date_allowed=df['Date'].min(),
                max_date_allowed=df['Date'].max(),
                initial_visible_month=df['Date'].min(),
            ),
            html.Div(id='date-range-output')
        ])
    else:
        graph = html.Div()
    
    return graph

def generate_corr_matrix(df):
    # Create a checklist for selecting variables
    checklist = dcc.Checklist(
        id='checklist-variables',
        options=[{'label': col, 'value': col} for col in df.columns],
        value=[df.columns[0]],  # Select the first option by default
        inline=True
    )
    return html.Div([checklist, html.Div(id='corr-matrix-container')])

@app.callback(Output('corr-matrix-container', 'children'),
              [Input('checklist-variables', 'value'),
               Input('data-store', 'data')])
def update_corr_matrix(selected_variables, data):
    if not selected_variables or data is None:
        return None
    
    df = pd.read_csv(io.StringIO(data))  # Convert CSV string to DataFrame
    selected_df = df[selected_variables]
    corr_matrix = selected_df.corr()
    heatmap = dcc.Graph(figure=px.imshow(corr_matrix))
    return heatmap

# Callback to hide the radio buttons when the "Correlation Matrix" tab is selected
@app.callback(Output('radio-select', 'style'),
              [Input('tabs', 'value')])
def hide_radio_buttons(selected_tab):
    if selected_tab == 'corr-matrix' or selected_tab == 'date-range-analysis':
        return {'display': 'none'}
    else:
        return {'display': 'inline-block'}

# Callback to update the date range output
@app.callback(Output('date-range-output', 'children'),
              [Input('date-range-picker', 'start_date'),
               Input('date-range-picker', 'end_date'),
               Input('data-store', 'data')],
              [State('date-range-table', 'data')])
def update_date_range_output(start_date, end_date, data, table_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    # Identify the trigger
    triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_input == 'date-range-picker' or triggered_input == 'data-store':
        if start_date is not None and end_date is not None and data is not None:
            df = pd.read_csv(io.StringIO(data))
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)  # Convert 'Date' column to datetime if it's not already
            
            # Filter the DataFrame based on the selected date range
            filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
            
             # Format the dates in the DataFrame
            filtered_df.loc[:, 'Date'] = pd.to_datetime(filtered_df['Date'], dayfirst=True).dt.strftime('%m/%d/%Y')
            
            # Generate statistics table for the selected date range
            statistics_table = filtered_df.describe(percentiles=[.25, .50, .75])
            statistics_table.reset_index(inplace=True)
            statistics_table.rename(columns={'index': 'Statistic'}, inplace=True)
            statistics_table = html.Div([
                html.Hr(),
                html.H2("Statistics for Selected Date Range", style={'textAlign': 'center'}),
                dash_table.DataTable(
                    data=statistics_table.to_dict('records'),
                    columns=[{'name': col, 'id': col} for col in statistics_table.columns],
                    style_table={'margin': 'auto', 'border': '2px solid black'},
                    style_cell={'textAlign': 'center', 'padding': '8px'},
                    style_header={'textAlign': 'center'}
                )
            ])
            
            # Return both date range table and statistics table stacked vertically
            return html.Div([
                dash_table.DataTable(
                    id='date-range-table',
                    data=filtered_df.to_dict('records'),  # Update table data with filtered DataFrame
                    columns=[{'name': i, 'id': i, 'editable': True} for i in filtered_df.columns],
                    page_size=10,
                    style_table={'margin': 'auto', 'border': '2px solid black'},
                    style_cell={'textAlign': 'center', 'padding': '8px'},
                    style_header={'textAlign': 'center'}
                ),
                html.Div([
                    html.A(
                        'Download CSV',
                        id='download-csv-link',
                        download="date_range_table.csv",
                        href="",
                        target="_blank",
                    ),
                    html.A(
                        'Download PDF',
                        id='download-pdf-link',
                        download="date_range_analysis.pdf",
                        href="",
                        target="_blank",
                        style={'margin-left': '20px'}  # Add some margin between the links
                    )
                ]),
                statistics_table
            ])
        else:
            return "Select a Date Range"
    else:
        return dash.no_update

# Callback to update download link href for CSV
@app.callback(
    Output('download-csv-link', 'href'),
    [Input('date-range-table', 'data'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')],
    [State('data-store', 'data')])
def update_download_csv_link(data, start_date, end_date, stored_data):
    if start_date is not None and end_date is not None and stored_data is not None:
        df = pd.read_csv(io.StringIO(stored_data))
        df['Date'] = pd.to_datetime(df['Date'])
        filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        csv_string = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        csv_string = "data:text/csv;charset=utf-8-sig," + quote(csv_string)
        return csv_string
    else:
        return ""

# Function to generate PDF from CSV data
def generate_pdf(csv_data, pdf_filename):
    pdf = SimpleDocTemplate(pdf_filename, pagesize=letter)
    data = []
    for line in csv_data.split('\n'):
        data.append(line.split(','))
    table = Table(data)
    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)])
    table.setStyle(style)
    pdf.build([table])

# Callback to update download link href for PDF
@app.callback(
    Output('download-pdf-link', 'href'),
    [Input('date-range-table', 'data'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')],
    [State('data-store', 'data')])
def update_download_pdf_link(data, start_date, end_date, stored_data):
    if start_date is not None and end_date is not None and stored_data is not None:
        df = pd.read_csv(io.StringIO(stored_data))
        df['Date'] = pd.to_datetime(df['Date'])
        filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        csv_data = filtered_df.to_csv(index=False)
        pdf_filename = "date_range_analysis.pdf"
        generate_pdf(csv_data, pdf_filename)
        pdf_string = "data:application/pdf;charset=utf-8," + quote(open(pdf_filename, 'rb').read())
        return pdf_string
    else:
        return ""

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True, port=8052)


# In[ ]:




