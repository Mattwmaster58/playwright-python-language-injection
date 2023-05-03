import inspect
from itertools import starmap
from pathlib import Path
from typing import Callable

import playwright.async_api._generated as aapi
import playwright.sync_api._generated as api
from playwright._repo_version import version


def additional_method_matches(additional_methods: dict[str, int], fn: Callable, fn_name: str, expected_arg_type: type):
    if fn_name in additional_methods:
        pos = additional_methods[fn_name]
        fn_annotations = fn.__annotations__
        if [*fn_annotations.values()][pos] == expected_arg_type:
            return True
        else:
            print(
                f"warning: {fn=} arg={[*fn_annotations.items()][pos]} does not match required type {expected_arg_type}")
    return False


def generate_css_js_injections() -> tuple[list[tuple[str, int, str]], ...]:
    """
    Generates of list of (method, argument index, module) for both CSS and JS based on the function argument names,
    types, as well as a list of edge cases. This tuple is necessary to configure language injections for IntelliJ IDEs
    """
    css_found = []
    js_found = []

    # these are language injections for methods that do not follow variable naming conventions
    additional_js_to_idx = {}

    additional_css_to_idx = {
        "drag_and_drop": 1
    }

    # since playwright is consistent with how they name all css selector args "selector", we can simply look for that
    CSS_SELECTOR_ARG_NAME = "selector"
    CSS_SELECTOR_ARG_TYPE = str

    JS_EXPRESSION_ARG_NAME = "expression"
    JS_EXPRESSION_ARG_TYPE = str

    for a in [api, aapi]:
        classes = [cls for cls in a.__dict__.values() if isinstance(cls, type)]
        for c in classes:
            methods = inspect.getmembers(c, predicate=inspect.isfunction)
            for fn_name, fn in methods:
                fn_annotations = fn.__annotations__
                if additional_method_matches(additional_js_to_idx, fn, fn_name, JS_EXPRESSION_ARG_TYPE):
                    js_found.append((fn_name, additional_js_to_idx[fn_name], f"{c.__module__}.{c.__name__}"))
                if additional_method_matches(additional_css_to_idx, fn, fn_name, CSS_SELECTOR_ARG_TYPE):
                    css_found.append((fn_name, additional_css_to_idx[fn_name], f"{c.__module__}.{c.__name__}"))

                for pos, (arg, type_) in enumerate(fn_annotations.items()):
                    if arg == CSS_SELECTOR_ARG_NAME and type_ == CSS_SELECTOR_ARG_TYPE:
                        css_found.append((fn_name, pos, f"{c.__module__}.{c.__name__}"))
                    elif arg == JS_EXPRESSION_ARG_NAME and type_ == JS_EXPRESSION_ARG_TYPE:
                        js_found.append((fn_name, pos, f"{c.__module__}.{c.__name__}"))

    return css_found, js_found


def generate_expression(method: str, index: int, module: str) -> str:
    return f'+ pyLiteralExpression().and(pyMethodArgument("{method}", {index}, "{module}"))'


def generate_xml(method: str, index: int, module: str) -> str:
    return f"<place><![CDATA[{generate_expression(method, index, module)}]]></place>"


def main():
    language_injection_template = """
    <LanguageInjectionConfiguration>
      <injection language="{language}" injector-id="python">
        <display-name>{name}</display-name>
        <single-file value="false" />
        {places}
        </injection>
    </LanguageInjectionConfiguration>
    """
    css, js = generate_css_js_injections()
    css.sort()
    js.sort()
    print(f"generated {len(css)} css and {len(js)} js language injection definitions")
    css_file_name = f"playwright-{version}-css.xml"
    Path(css_file_name).write_text(language_injection_template.format(
        language="CSS",
        name="playwright - CSS",
        places="\n".join(starmap(generate_xml, css))
    ))
    js_file_name = f"playwright-{version}-js.xml"
    Path(js_file_name).write_text(language_injection_template.format(
        language="javascript",
        name="playwright - JS",
        places="\n".join(starmap(generate_xml, js))
    ))
    print(f"wrote output files: {css_file_name}, {js_file_name}")


if __name__ == '__main__':
    main()
