from opensearchpy import OpenSearch, RequestsHttpConnection


def create_opensearch_client(app=None):
    try:
        client = OpenSearch(
            hosts=[
                {
                    "host": app.config["OPENSEARCH_HOST"],
                    "port": app.config["OPENSEARCH_PORT"],
                }
            ],
            http_auth=(
                app.config["OPENSEARCH_AUTH_ADMIN"],
                app.config["OPENSEARCH_INITIAL_ADMIN_PASSWORD"],
            ),
            use_ssl=False,
            connection_class=RequestsHttpConnection,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
    except ConnectionError as e:
        app.logger.error(f"OpenSearch connection failed: {e}")
        return None

    return client
