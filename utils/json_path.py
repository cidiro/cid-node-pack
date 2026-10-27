def split_json_path(path):
    segments = path.split("/")
    if any(segment == "" for segment in segments):
        raise ValueError(f"Input 'key' contains an empty path segment: '{path}'.")
    return segments


def _path_label(segments):
    return "/".join(segments)


def _is_list_index(segment):
    body = segment[1:] if segment.startswith("-") else segment
    return body.isdigit()


def _require_list_index(segment, full_path, path):
    if not _is_list_index(segment):
        raise TypeError(
            f"The key path '{full_path}' expected a list index at '{path}', "
            f"but got '{segment}'."
        )
    return int(segment)


def _resolve_list_index(index, items, full_path, path):
    """Resolve a possibly-negative index against the list length, Python-style."""
    length = len(items)
    resolved = index + length if index < 0 else index
    if resolved < 0 or resolved >= length:
        raise IndexError(
            f"The key path '{full_path}' has list index {index} out of range at '{path}'. "
            f"List length: {length}"
        )
    return resolved


def _get_list_item(items, index, full_path, path):
    return items[_resolve_list_index(index, items, full_path, path)]


def get_json_path_value(data, key):
    if key in data:
        return data[key]

    current = data
    traversed = []

    for segment in split_json_path(key):
        path = _path_label(traversed + [segment])

        if isinstance(current, dict):
            if segment not in current:
                raise KeyError(
                    f"The key path '{key}' could not be resolved at '{path}'. "
                    f"Available keys: {list(current.keys())}"
                )
            current = current[segment]
        elif isinstance(current, list):
            index = _require_list_index(segment, key, path)
            current = _get_list_item(current, index, key, path)
        else:
            parent_path = _path_label(traversed)
            raise TypeError(
                f"The key path '{key}' could not continue at '{path}' because "
                f"'{parent_path}' is a {type(current).__name__}, not an object or list."
            )

        traversed.append(segment)

    return current


def set_json_path_value(data, key, value):
    if key in data:
        data[key] = value
        return

    segments = split_json_path(key)
    if len(segments) == 1:
        data[key] = value
        return

    current = data
    traversed = []

    for index, segment in enumerate(segments[:-1]):
        path = _path_label(traversed + [segment])
        next_segment = segments[index + 1]

        if isinstance(current, dict):
            if segment not in current:
                if _is_list_index(next_segment):
                    raise TypeError(
                        f"The key path '{key}' requires an existing list at '{path}'. "
                        "Missing list parents are not created automatically."
                    )
                current[segment] = {}
            current = current[segment]
        elif isinstance(current, list):
            item_index = _require_list_index(segment, key, path)
            current = _get_list_item(current, item_index, key, path)
        else:
            parent_path = _path_label(traversed)
            raise TypeError(
                f"The key path '{key}' could not continue at '{path}' because "
                f"'{parent_path}' is a {type(current).__name__}, not an object or list."
            )

        traversed.append(segment)

    final_segment = segments[-1]
    final_path = _path_label(traversed + [final_segment])

    if isinstance(current, dict):
        current[final_segment] = value
    elif isinstance(current, list):
        index = _require_list_index(final_segment, key, final_path)
        current[_resolve_list_index(index, current, key, final_path)] = value
    else:
        parent_path = _path_label(traversed)
        raise TypeError(
            f"The key path '{key}' could not set '{final_path}' because "
            f"'{parent_path}' is a {type(current).__name__}, not an object or list."
        )


def append_json_path_value(data, key, value):
    if key in data:
        if not isinstance(data[key], list):
            raise TypeError(
                f"The key '{key}' exists but is a {type(data[key]).__name__}, not a list."
            )
        data[key].append(value)
        return

    segments = split_json_path(key)
    if len(segments) == 1:
        data[key] = [value]
        return

    current = data
    traversed = []

    for index, segment in enumerate(segments[:-1]):
        path = _path_label(traversed + [segment])
        next_segment = segments[index + 1]

        if isinstance(current, dict):
            if segment not in current:
                if _is_list_index(next_segment):
                    raise TypeError(
                        f"The key path '{key}' requires an existing list at '{path}'. "
                        "Missing list parents are not created automatically."
                    )
                current[segment] = {}
            current = current[segment]
        elif isinstance(current, list):
            item_index = _require_list_index(segment, key, path)
            current = _get_list_item(current, item_index, key, path)
        else:
            parent_path = _path_label(traversed)
            raise TypeError(
                f"The key path '{key}' could not continue at '{path}' because "
                f"'{parent_path}' is a {type(current).__name__}, not an object or list."
            )

        traversed.append(segment)

    final_segment = segments[-1]
    final_path = _path_label(traversed + [final_segment])

    if isinstance(current, dict):
        if final_segment not in current:
            current[final_segment] = [value]
            return
        target = current[final_segment]
    elif isinstance(current, list):
        index = _require_list_index(final_segment, key, final_path)
        target = _get_list_item(current, index, key, final_path)
    else:
        parent_path = _path_label(traversed)
        raise TypeError(
            f"The key path '{key}' could not append to '{final_path}' because "
            f"'{parent_path}' is a {type(current).__name__}, not an object or list."
        )

    if not isinstance(target, list):
        raise TypeError(
            f"The key path '{key}' resolved to a {type(target).__name__} at "
            f"'{final_path}', not a list."
        )

    target.append(value)


def remove_json_path_value(data, key):
    if key in data:
        del data[key]
        return True

    segments = split_json_path(key)
    if len(segments) == 1:
        return False

    current = data
    traversed = []

    for segment in segments[:-1]:
        path = _path_label(traversed + [segment])

        if isinstance(current, dict):
            if segment not in current:
                return False
            current = current[segment]
        elif isinstance(current, list):
            index = _require_list_index(segment, key, path)
            current = _get_list_item(current, index, key, path)
        else:
            parent_path = _path_label(traversed)
            raise TypeError(
                f"The key path '{key}' could not continue at '{path}' because "
                f"'{parent_path}' is a {type(current).__name__}, not an object or list."
            )

        traversed.append(segment)

    final_segment = segments[-1]
    final_path = _path_label(traversed + [final_segment])

    if isinstance(current, dict):
        if final_segment not in current:
            return False
        del current[final_segment]
        return True

    if isinstance(current, list):
        index = _require_list_index(final_segment, key, final_path)
        del current[_resolve_list_index(index, current, key, final_path)]
        return True

    parent_path = _path_label(traversed)
    raise TypeError(
        f"The key path '{key}' could not remove '{final_path}' because "
        f"'{parent_path}' is a {type(current).__name__}, not an object or list."
    )
