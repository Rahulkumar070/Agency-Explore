"""Agency discovery, proposal, and delivery workflows."""


def register(ctx):
    from .hermes import register as register_command
    register_command(ctx)
