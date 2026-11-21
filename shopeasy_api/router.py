import re
from typing import Callable, Dict, List, Tuple
from shopeasy_api.errors import ApiError

RouteHandler = Callable[..., Tuple[int, object]]


class Router:
    def __init__(self) -> None:
        # Each entry: (compiled_regex, param_names, methods_dict)
        self._routes: List[Tuple[re.Pattern, List[str], Dict[str, RouteHandler]]] = []

    def add_route(self, pattern: str, methods: Dict[str, RouteHandler]) -> None:
        param_names = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", pattern)
        regex_str = "^" + re.sub(
            r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}",
            r"(?P<\1>[^/]+)",
            pattern,
        ) + "$"
        compiled = re.compile(regex_str)
        self._routes.append((compiled, param_names, methods))

    def resolve(self, method: str, path: str) -> Tuple[RouteHandler, Dict[str, str]]:
        path_matched_with_wrong_method = False
        for compiled, _param_names, methods in self._routes:
            match = compiled.match(path)
            if match:
                if method in methods:
                    return methods[method], match.groupdict()
                path_matched_with_wrong_method = True

        if path_matched_with_wrong_method:
            raise ApiError(405, f"Method {method} not allowed for {path}")
        raise ApiError(404, f"Route not found: {path}")