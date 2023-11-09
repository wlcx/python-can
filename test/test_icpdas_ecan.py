from can.message import Message
from can.interfaces.icpdas_ecan import encode_message, decode_message
import pytest

@pytest.mark.parametrize(("id_", "remote", "extended", "data"), [
    (0, False, False, []),
    (13, True, False, []),
    (2047, False, False, [1,2,3,4]),
    (2047, False, False, [1,2,3,4,5,6,7,8]),
    (12345, False, True, [1,2,3,4,5,6,7,8]),
    (12345, True, True, []),
])
def test_encode_decode(id_, remote, extended, data):
    """Test that a message is encoded and decoded the same."""
    d = [1, 2, 3, 4, 5, 6, 7, 8]
    m = Message(
        arbitration_id=id_,
        is_extended_id=extended,
        is_remote_frame=remote,
        data = bytes(data),
        dlc=len(data),
    )

    assert decode_message(encode_message(m).strip(b"\r")).equals(m)