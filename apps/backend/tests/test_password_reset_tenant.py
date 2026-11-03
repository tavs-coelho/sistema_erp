from unittest.mock import MagicMock, patch
from app.routers.auth import request_password_reset
from app.schemas import PasswordResetRequest


def test_reset_request_does_not_disclose_cross_tenant_user():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    result = request_password_reset(PasswordResetRequest(username="other-tenant-user"), db=db, tenant_id=42)
    assert result == {"message": "Se usuário existir, o reset foi gerado"}
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_reset_request_filters_by_tenant():
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    request_password_reset(PasswordResetRequest(username="missing"), db=db, tenant_id=42)
    assert db.query.return_value.filter.return_value.filter.called
