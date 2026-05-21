"""Domain value objects.

Value objects are immutable and compared by value rather than identity.
Place concrete value object classes (e.g. EmailAddress, Money) in this package.
"""

from domain.value_objects.upload_status import UploadStatus


__all__: list[str] = ["UploadStatus"]
