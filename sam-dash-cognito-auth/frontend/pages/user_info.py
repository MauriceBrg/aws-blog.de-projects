import dash
import dash_bootstrap_components as dbc
from dash import html
from flask import session


dash.register_page(__name__, path="/", name="User Info")


def layout():

    content = []

    logged_in_user_email = session["email"]

    user_info = html.Ul(
        [
            html.Li(["Logged in as: ", html.Strong(logged_in_user_email)]),
        ],
    )

    content.append(user_info)

    content.append(html.A(href="/logout", children=["Logout"]))

    return dbc.Container(content)
