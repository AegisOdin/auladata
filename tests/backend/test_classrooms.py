import pytest
from app.models import Classroom, ClassroomStatus
from app.repositories import classrooms as repository
from conftest import CSRF


def test_authenticated_list_is_paginated(admin_client, classroom_id):
    response = admin_client.get("/api/v1/classrooms")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 20
    assert response.json()["items"][0]["id"] == classroom_id


def test_admin_creates_valid_classroom(admin_client, classroom_payload):
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload, headers=CSRF)
    assert response.status_code == 201
    item = response.json()
    assert item["id"] > 0
    assert item["clave"] == "ISC-A01"
    assert item["deleted_at"] is None
    assert item["created_at"] and item["updated_at"]


def test_duplicate_normalized_key_is_conflict(admin_client, classroom_id, classroom_payload):
    classroom_payload["clave"] = " isc-a01 "
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload, headers=CSRF)
    assert response.status_code == 409


def test_duplicate_after_precheck_is_still_conflict(
    admin_client, classroom_id, classroom_payload, monkeypatch
):
    # Simulate another writer inserting after the optimistic uniqueness check.
    monkeypatch.setattr(repository, "key_exists", lambda *args, **kwargs: False)
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload, headers=CSRF)
    assert response.status_code == 409
    assert admin_client.get("/api/v1/classrooms").json()["total"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("capacidad", 0),
        ("capacidad", -1),
        ("capacidad", 2.5),
        ("capacidad", True),
        ("capacidad", 2147483648),
        ("nombre", "   "),
        ("clave", "x" * 21),
        ("nombre", "x" * 101),
        ("edificio", "x" * 51),
        ("tipo", "INVALIDA"),
        ("estado", "BORRADA"),
        ("id", 10),
    ],
)
def test_invalid_classroom_is_rejected(admin_client, classroom_payload, field, value):
    classroom_payload[field] = value
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload, headers=CSRF)
    assert response.status_code == 422
    assert admin_client.get("/api/v1/classrooms").json()["total"] == 0


def test_admin_updates_classroom(admin_client, classroom_id):
    response = admin_client.patch(
        f"/api/v1/classrooms/{classroom_id}",
        json={"nombre": "Laboratorio actualizado", "capacidad": 42},
        headers=CSRF,
    )
    assert response.status_code == 200
    assert response.json()["nombre"] == "Laboratorio actualizado"
    assert response.json()["capacidad"] == 42
    assert response.json()["clave"] == "ISC-A01"


def test_admin_replaces_classroom(admin_client, classroom_id, classroom_payload):
    classroom_payload["edificio"] = "Edificio Nuevo"
    response = admin_client.put(
        f"/api/v1/classrooms/{classroom_id}", json=classroom_payload, headers=CSRF
    )
    assert response.status_code == 200
    assert response.json()["edificio"] == "Edificio Nuevo"


@pytest.mark.parametrize("payload", [{}, {"capacidad": None}, {"nombre": None}, {"role": "ADMIN"}])
def test_patch_rejects_empty_null_and_unexpected_fields(admin_client, classroom_id, payload):
    response = admin_client.patch(f"/api/v1/classrooms/{classroom_id}", json=payload, headers=CSRF)
    assert response.status_code == 422


def test_soft_delete_preserves_row_and_hides_it(admin_client, classroom_id, application):
    response = admin_client.delete(f"/api/v1/classrooms/{classroom_id}", headers=CSRF)
    assert response.status_code == 204
    assert response.content == b""
    assert admin_client.get("/api/v1/classrooms").json()["items"] == []
    assert admin_client.get(f"/api/v1/classrooms/{classroom_id}").status_code == 404
    with application.state.session_factory() as session:
        row = session.get(Classroom, classroom_id)
        assert row is not None
        assert row.deleted_at is not None
        assert row.estado == ClassroomStatus.INACTIVA


def test_deleted_key_cannot_be_reused(admin_client, classroom_id, classroom_payload):
    assert (
        admin_client.delete(f"/api/v1/classrooms/{classroom_id}", headers=CSRF).status_code == 204
    )
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload, headers=CSRF)
    assert response.status_code == 409


def test_viewer_can_list_and_read(viewer_client, classroom_id):
    assert viewer_client.get("/api/v1/classrooms").status_code == 200
    assert viewer_client.get(f"/api/v1/classrooms/{classroom_id}").status_code == 200


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_viewer_cannot_mutate(viewer_client, classroom_id, classroom_payload, method):
    path = "/api/v1/classrooms" if method == "post" else f"/api/v1/classrooms/{classroom_id}"
    arguments = {"headers": CSRF}
    if method != "delete":
        arguments["json"] = classroom_payload
    response = getattr(viewer_client, method)(path, **arguments)
    assert response.status_code == 403


def test_admin_mutation_requires_csrf_header(admin_client, classroom_payload):
    response = admin_client.post("/api/v1/classrooms", json=classroom_payload)
    assert response.status_code == 403


def test_missing_classroom_is_404(admin_client):
    assert admin_client.get("/api/v1/classrooms/999999").status_code == 404


def test_search_filters_and_pagination(admin_client, classroom_payload):
    for index, tipo, estado in [
        (1, "LABORATORIO", "ACTIVA"),
        (2, "TEORICA", "MANTENIMIENTO"),
        (3, "LABORATORIO", "ACTIVA"),
    ]:
        payload = {**classroom_payload, "clave": f"ISC-A0{index}", "tipo": tipo, "estado": estado}
        assert (
            admin_client.post("/api/v1/classrooms", json=payload, headers=CSRF).status_code == 201
        )
    response = admin_client.get(
        "/api/v1/classrooms?search=isc&tipo=LABORATORIO&estado=ACTIVA&page=2&page_size=1"
    )
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["clave"] == "ISC-A03"
    assert admin_client.get("/api/v1/classrooms?search=%25").json()["total"] == 0


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "estado=UNKNOWN", "tipo=UNKNOWN"])
def test_invalid_list_parameters_are_rejected(admin_client, query):
    assert admin_client.get(f"/api/v1/classrooms?{query}").status_code == 422
