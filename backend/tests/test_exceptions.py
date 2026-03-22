from app.exceptions import AppError, NotFoundError, InvalidTransitionError, ValidationError


def test_not_found_error_has_404_status():
    err = NotFoundError("Issue not found")
    assert err.status_code == 404
    assert err.message == "Issue not found"
    assert isinstance(err, AppError)


def test_invalid_transition_error_has_409_status():
    err = InvalidTransitionError("Cannot transition from New to Finished")
    assert err.status_code == 409
    assert err.message == "Cannot transition from New to Finished"


def test_validation_error_has_422_status():
    err = ValidationError("Recap cannot be blank")
    assert err.status_code == 422
    assert err.message == "Recap cannot be blank"


def test_app_error_base_has_500_status():
    err = AppError("Something went wrong")
    assert err.status_code == 500
