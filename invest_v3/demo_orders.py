"""Boundary reserved for explicitly authorized Trading 212 Demo execution."""


def submit(*args, **kwargs):
    raise PermissionError("Invio ordini Demo disabilitato. Usare la simulazione interna.")
