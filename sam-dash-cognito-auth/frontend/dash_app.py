import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

from auth import add_cognito_auth_to


def render_nav() -> dbc.Navbar:

    page_links = [
        dbc.NavItem(children=[dbc.NavLink(page["name"], href=page["relative_path"])])
        for page in dash.page_registry.values()
    ]

    nav = dbc.Navbar(
        dbc.Container(
            children=[
                *page_links,
                dbc.NavItem(
                    dbc.NavLink(
                        "tecRacer",
                        href="https://www.tecracer.com/",
                        external_link=True,
                        target="_blank",
                    )
                ),
            ]
        ),
        class_name="mb-3",
        dark=True,
    )

    return nav


def build_app(dash_kwargs: dict = None) -> Dash:

    dash_kwargs = dash_kwargs or {}

    app = Dash(
        name=__name__,
        use_pages=True,
        external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
        **dash_kwargs,
    )

    app.layout = html.Div(
        children=[
            render_nav(),
            dash.page_container,
        ],
    )

    app.server.secret_key = "CHANGE_ME"

    add_cognito_auth_to(app)

    return app


if __name__ == "__main__":
    build_app().run(debug=True)
