"""Domain services.

Contains domain logic that does not naturally belong to a single entity.
Domain services are stateless and operate only on domain objects.

Example:
    class PricingService:
        def calculate_discount(self, item: Item, coupon: Coupon) -> Money:
            ...
"""

__all__: list[str] = []
