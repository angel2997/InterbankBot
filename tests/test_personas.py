from repositories.persona_repository import (
    PersonaRepository,
)


repository = PersonaRepository()

repository.create_table()

first_insert = (
    repository.create_permanent_people()
)

second_insert = (
    repository.create_permanent_people()
)

people = repository.list_permanent_people()

print("=" * 60)
print("PERSONAS PERMANENTES")
print("=" * 60)

print("Primera inserción:", first_insert)
print("Segunda inserción:", second_insert)
print("Total:", len(people))
print()

for person in people:
    print(
        person["id"],
        person["nombre"],
        "Permanente:",
        bool(person["permanente"]),
    )