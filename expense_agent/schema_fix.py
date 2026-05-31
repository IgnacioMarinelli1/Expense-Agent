import logging

logger = logging.getLogger("expense_agent.schema_fix")


def _deep_strip_schema(schema):
    if schema is None:
        return
    before = getattr(schema, 'additional_properties', 'MISSING')
    try:
        schema.additional_properties = None
    except Exception as e:
        logger.warning("Could not clear additional_properties on %s: %s", type(schema), e)
    after = getattr(schema, 'additional_properties', 'MISSING')
    if before not in (None, 'MISSING'):
        logger.info("Stripped additional_properties on %s: %r -> %r", type(schema).__name__, before, after)

    props = getattr(schema, 'properties', None) or {}
    for name, sub in props.items():
        _deep_strip_schema(sub)
    if getattr(schema, 'items', None):
        _deep_strip_schema(schema.items)
    for sub in (getattr(schema, 'any_of', None) or []):
        _deep_strip_schema(sub)


def strip_schemas_callback(callback_context, llm_request):
    config = getattr(llm_request, 'config', None)
    tools = getattr(config, 'tools', None) or []
    fd_count = sum(len(getattr(t, 'function_declarations', None) or []) for t in tools)
    logger.info("strip_schemas_callback called: %d tool groups, %d function declarations", len(tools), fd_count)
    for tool in tools:
        for fd in (getattr(tool, 'function_declarations', None) or []):
            params = getattr(fd, 'parameters', None)
            if params is not None:
                logger.debug("Processing fd=%s parameters type=%s", getattr(fd, 'name', '?'), type(params).__name__)
                _deep_strip_schema(params)
    logger.info("strip_schemas_callback done")
    return None


# Nuclear patch: ensure Schema.model_dump never emits additional_properties.
# This catches any version of google-genai that includes the field even when null.
def _patch_schema_model_dump():
    try:
        from google.genai import types as _gt
        _orig = _gt.Schema.model_dump

        def _safe_dump(self, **kwargs):
            result = _orig(self, **kwargs)
            removed = result.pop('additional_properties', None)
            result.pop('additionalProperties', None)
            if removed is not None:
                logger.debug("model_dump patch removed additional_properties=%r from Schema", removed)
            return result

        _gt.Schema.model_dump = _safe_dump
        logger.info("Schema.model_dump patched to strip additional_properties")
    except Exception as e:
        logger.warning("Could not patch Schema.model_dump: %s", e)


_patch_schema_model_dump()
