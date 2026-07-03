def split_json_path(path):
    segments = path.split("/")
    if any(segment == "" for segment in segments):
        raise ValueError(f"Input 'key' contains an empty path segment: '{path}'.")
    return segments


def _path_label(segments):
    return "/".join(segments)


def _require_list_index(segment, full_path, path):
    if not segment.isdigit():
        raise TypeError(
            f"The key path '{full_path}' expected a non-negative list index at '{path}', "
            f"but got '{segment}'."
        )
    return int(segment)


def _get_list_item(items, index, full_path, path):
    if index >= len(items):
        raise IndexError(
            f"The key path '{full_path}' has list index {index} out of range at '{path}'. "
            f"List length: {len(items)}"
        )
    return items[index]


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
                if next_segment.isdigit():
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
        if index >= len(current):
            raise IndexError(
                f"The key path '{key}' has list index {index} out of range at '{final_path}'. "
                f"List length: {len(current)}"
            )
        current[index] = value
    else:
        parent_path = _path_label(traversed)
        raise TypeError(
            f"The key path '{key}' could not set '{final_path}' because "
            f"'{parent_path}' is a {type(current).__name__}, not an object or list."
        )


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
        if index >= len(current):
            raise IndexError(
                f"The key path '{key}' has list index {index} out of range at '{final_path}'. "
                f"List length: {len(current)}"
            )
        del current[index]
        return True

    parent_path = _path_label(traversed)
    raise TypeError(
        f"The key path '{key}' could not remove '{final_path}' because "
        f"'{parent_path}' is a {type(current).__name__}, not an object or list."
    )
