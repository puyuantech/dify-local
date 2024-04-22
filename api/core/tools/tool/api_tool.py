import json
from json import dumps
from os import getenv
from typing import Any, Union
from urllib.parse import urlencode

import httpx
import requests

import core.helper.ssrf_proxy as ssrf_proxy
from core.tools.entities.tool_bundle import ApiBasedToolBundle
from core.tools.entities.tool_entities import ToolInvokeMessage, ToolProviderType
from core.tools.entities.user_entities import UserToolProvider
from core.tools.errors import ToolInvokeError, ToolParameterValidationError, ToolProviderCredentialValidationError
from core.tools.tool.tool import Tool

API_TOOL_DEFAULT_TIMEOUT = (
    int(getenv('API_TOOL_DEFAULT_CONNECT_TIMEOUT', '10')),
    int(getenv('API_TOOL_DEFAULT_READ_TIMEOUT', '60'))
)

class ApiTool(Tool):
    api_bundle: ApiBasedToolBundle
    
    """
    Api tool
    """
    def fork_tool_runtime(self, meta: dict[str, Any]) -> 'Tool':
        """
            fork a new tool with meta data

            :param meta: the meta data of a tool call processing, tenant_id is required
            :return: the new tool
        """
        return self.__class__(
            identity=self.identity.copy() if self.identity else None,
            parameters=self.parameters.copy() if self.parameters else None,
            description=self.description.copy() if self.description else None,
            api_bundle=self.api_bundle.copy() if self.api_bundle else None,
            runtime=Tool.Runtime(**meta)
        )
    
    def validate_credentials(self, credentials: dict[str, Any], parameters: dict[str, Any], format_only: bool = False) -> str:
        """
            validate the credentials for Api tool
        """
        # assemble validate request and request parameters 
        headers = self.assembling_request(parameters)

        if format_only:
            return

        response = self.do_http_request(self.api_bundle.server_url, self.api_bundle.method, headers, parameters)
        # validate response
        return self.validate_and_parse_response(response)

    def tool_provider_type(self) -> ToolProviderType:
        return UserToolProvider.ProviderType.API

    def assembling_request(self, parameters: dict[str, Any]) -> dict[str, Any]:
        headers = {}
        credentials = self.runtime.credentials or {}

        if 'auth_type' not in credentials:
            raise ToolProviderCredentialValidationError('Missing auth_type')

        if credentials['auth_type'] == 'api_key':
            api_key_header = 'api_key'

            if 'api_key_header' in credentials:
                api_key_header = credentials['api_key_header']
            
            if 'api_key_value' not in credentials:
                raise ToolProviderCredentialValidationError('Missing api_key_value')
            elif not isinstance(credentials['api_key_value'], str):
                raise ToolProviderCredentialValidationError('api_key_value must be a string')
            
            if 'api_key_header_prefix' in credentials:
                api_key_header_prefix = credentials['api_key_header_prefix']
                if api_key_header_prefix == 'basic' and credentials['api_key_value']:
                    credentials['api_key_value'] = f'Basic {credentials["api_key_value"]}'
                elif api_key_header_prefix == 'bearer' and credentials['api_key_value']:
                    credentials['api_key_value'] = f'Bearer {credentials["api_key_value"]}'
                elif api_key_header_prefix == 'custom':
                    pass
            
            headers[api_key_header] = credentials['api_key_value']

        needed_parameters = [parameter for parameter in self.api_bundle.parameters if parameter.required]
        for parameter in needed_parameters:
            if parameter.required and parameter.name not in parameters:
                raise ToolParameterValidationError(f"Missing required parameter {parameter.name}")
            
            if parameter.default is not None and parameter.name not in parameters:
                parameters[parameter.name] = parameter.default

        return headers

    def validate_and_parse_response(self, response: Union[httpx.Response, requests.Response]) -> str:
        """
            validate the response
        """
        if isinstance(response, httpx.Response):
            if response.status_code >= 400:
                raise ToolInvokeError(f"Request failed with status code {response.status_code} and {response.text}")
            if not response.content:
                return 'Empty response from the tool, please check your parameters and try again.'
            try:
                response = response.json()
                try:
                    return json.dumps(response, ensure_ascii=False)
                except Exception as e:
                    return json.dumps(response)
            except Exception as e:
                return response.text
        elif isinstance(response, requests.Response):
            if not response.ok:
                raise ToolInvokeError(f"Request failed with status code {response.status_code} and {response.text}")
            if not response.content:
                return 'Empty response from the tool, please check your parameters and try again.'
            try:
                response = response.json()
                try:
                    return json.dumps(response, ensure_ascii=False)
                except Exception as e:
                    return json.dumps(response)
            except Exception as e:
                return response.text
        else:
            raise ValueError(f'Invalid response type {type(response)}')
    
    def do_http_request(self, url: str, method: str, headers: dict[str, Any], parameters: dict[str, Any]) -> httpx.Response:
        """
            do http request depending on api bundle
        """
        method = method.lower()

        params = {}
        path_params = {}
        body = {}
        cookies = {}

        # check parameters
        for parameter in self.api_bundle.openapi.get('parameters', []):
            if parameter['in'] == 'path':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter['required']:
                    raise ToolParameterValidationError(f"Missing required parameter {parameter['name']}")
                else:
                    value = (parameter.get('schema', {}) or {}).get('default', '')
                path_params[parameter['name']] = value

            elif parameter['in'] == 'query':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter.get('required', False):
                    raise ToolParameterValidationError(f"Missing required parameter {parameter['name']}")
                else:
                    value = (parameter.get('schema', {}) or {}).get('default', '')
                params[parameter['name']] = value

            elif parameter['in'] == 'cookie':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter.get('required', False):
                    raise ToolParameterValidationError(f"Missing required parameter {parameter['name']}")
                else:
                    value = (parameter.get('schema', {}) or {}).get('default', '')
                cookies[parameter['name']] = value

            elif parameter['in'] == 'header':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter.get('required', False):
                    raise ToolParameterValidationError(f"Missing required parameter {parameter['name']}")
                else:
                    value = (parameter.get('schema', {}) or {}).get('default', '')
                headers[parameter['name']] = value

        # check if there is a request body and handle it
        if 'requestBody' in self.api_bundle.openapi and self.api_bundle.openapi['requestBody'] is not None:
            # handle json request body
            if 'content' in self.api_bundle.openapi['requestBody']:
                for content_type in self.api_bundle.openapi['requestBody']['content']:
                    headers['Content-Type'] = content_type
                    body_schema = self.api_bundle.openapi['requestBody']['content'][content_type]['schema']
                    required = body_schema['required'] if 'required' in body_schema else []
                    properties = body_schema['properties'] if 'properties' in body_schema else {}
                    for name, property in properties.items():
                        if name in parameters:
                            # convert type
                            body[name] = self._convert_body_property_type(property, parameters[name])
                        elif name in required:
                            raise ToolParameterValidationError(
                                f"Missing required parameter {name} in operation {self.api_bundle.operation_id}"
                            )
                        elif 'default' in property:
                            body[name] = property['default']
                        else:
                            body[name] = None
                    break
        
        # replace path parameters
        for name, value in path_params.items():
            url = url.replace(f'{{{name}}}', f'{value}')

        # parse http body data if needed, for GET/HEAD/OPTIONS/TRACE, the body is ignored
        if 'Content-Type' in headers:
            if headers['Content-Type'] == 'application/json':
                body = dumps(body)
            elif headers['Content-Type'] == 'application/x-www-form-urlencoded':
                body = urlencode(body)
            else:
                body = body
        
        # do http request
        if method == 'get':
            response = ssrf_proxy.get(url, params=params, headers=headers, cookies=cookies, timeout=API_TOOL_DEFAULT_TIMEOUT, follow_redirects=True)
        elif method == 'post':
            response = ssrf_proxy.post(url, params=params, headers=headers, cookies=cookies, data=body, timeout=API_TOOL_DEFAULT_TIMEOUT, follow_redirects=True)
        elif method == 'put':
            response = ssrf_proxy.put(url, params=params, headers=headers, cookies=cookies, data=body, timeout=API_TOOL_DEFAULT_TIMEOUT, follow_redirects=True)
        elif method == 'delete':
            response = ssrf_proxy.delete(url, params=params, headers=headers, cookies=cookies, data=body, timeout=API_TOOL_DEFAULT_TIMEOUT, allow_redirects=True)
        elif method == 'patch':
            response = ssrf_proxy.patch(url, params=params, headers=headers, cookies=cookies, data=body, timeout=API_TOOL_DEFAULT_TIMEOUT, follow_redirects=True)
        elif method == 'head':
            response = ssrf_proxy.head(url, params=params, headers=headers, cookies=cookies, timeout=API_TOOL_DEFAULT_TIMEOUT, follow_redirects=True)
        elif method == 'options':
            response = ssrf_proxy.options(url, params=params, headers=headers, cookies=cookies, timeout=API_TOOL_DEFAULT_TIMEOUT, follow_redirects=True)
        else:
            raise ValueError(f'Invalid http method {method}')
        
        return response
    
    def _convert_body_property_any_of(self, property: dict[str, Any], value: Any, any_of: list[dict[str, Any]], max_recursive=10) -> Any:
        if max_recursive <= 0:
            raise Exception("Max recursion depth reached")
        for option in any_of or []:
            try:
                if 'type' in option:
                    # Attempt to convert the value based on the type.
                    if option['type'] == 'integer' or option['type'] == 'int':
                        return int(value)
                    elif option['type'] == 'number':
                        if '.' in str(value):
                            return float(value)
                        else:
                            return int(value)
                    elif option['type'] == 'string':
                        return str(value)
                    elif option['type'] == 'boolean':
                        if str(value).lower() in ['true', '1']:
                            return True
                        elif str(value).lower() in ['false', '0']:
                            return False
                        else:
                            continue  # Not a boolean, try next option
                    elif option['type'] == 'null' and not value:
                        return None
                    else:
                        continue  # Unsupported type, try next option
                elif 'anyOf' in option and isinstance(option['anyOf'], list):
                    # Recursive call to handle nested anyOf
                    return self._convert_body_property_any_of(property, value, option['anyOf'], max_recursive - 1)
            except ValueError:
                continue  # Conversion failed, try next option
        # If no option succeeded, you might want to return the value as is or raise an error
        return value  # or raise ValueError(f"Cannot convert value '{value}' to any specified type in anyOf")

    def _convert_body_property_type(self, property: dict[str, Any], value: Any) -> Any:
        try:
            if 'type' in property:
                if property['type'] == 'integer' or property['type'] == 'int':
                    return int(value)
                elif property['type'] == 'number':
                    # check if it is a float
                    if '.' in value:
                        return float(value)
                    else:
                        return int(value)
                elif property['type'] == 'string':
                    return str(value)
                elif property['type'] == 'boolean':
                    return bool(value)
                elif property['type'] == 'null':
                    if value is None:
                        return None
                elif property['type'] == 'object':
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except ValueError:
                            return value
                    elif isinstance(value, dict):
                        return value
                    else:
                        return value
                else:
                    raise ValueError(f"Invalid type {property['type']} for property {property}")
            elif 'anyOf' in property and isinstance(property['anyOf'], list):
                return self._convert_body_property_any_of(property, value, property['anyOf'])
        except ValueError as e:
            return value

    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage | list[ToolInvokeMessage]:
        """
        invoke http request
        """
        # assemble request
        headers = self.assembling_request(tool_parameters)

        # do http request
        response = self.do_http_request(self.api_bundle.server_url, self.api_bundle.method, headers, tool_parameters)

        # validate response
        response = self.validate_and_parse_response(response)

        # assemble invoke message
        return self.create_text_message(response)
    