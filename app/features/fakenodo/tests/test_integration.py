"""HTTP integration tests for the fakenodo feature.

Drive the application through the Flask test client. The ``test_client``
fixture rebuilds a clean DB per test for full isolation.
"""

import pytest

pytestmark = pytest.mark.integration


def test_fakenodo_index_responds(test_client):
    response = test_client.get("/fakenodo")
    assert response.status_code == 200, "/fakenodo did not return 200"
