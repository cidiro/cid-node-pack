# A custom type that equals any other type
# Credit to pythongossss for the AnyType trick
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        # Always return False so that this type never mismatches another
        return False

any_type = AnyType("*")