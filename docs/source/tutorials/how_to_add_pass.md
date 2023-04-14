(How-to-add-pass)=
# How to add new Pass

Olive provides simple interface to introduce new model optimization techniques. Each optimization technique is
represented as a Pass in Olive.

To introduce a new Pass follow these 3 steps.

## 1. Define a new class

Define a new class using Pass as the base class. For example

```python
from olive.passes import Pass

class NewOptimizationTrick(Pass):

    # set this to True if the pass has paremeters that are functions or objects and the user script is required
    # to import the module containing the function or object
    _requires_user_script: bool = False
```

## 2. Define configuration

Next, define the options used to configure this new technique by defining static method `_default_config`. The method should
return `Dict[str, PassConfigParam]`.

`PassConfigParam` is a dataclass that holds the information about the configuration option. The dataclass has the following fields:

- `type_` : type of the parameter

- `required` : whether the parameter is required

- `is_object` : whether the parameter is an object/function. If so, this parameter accepts the object or a string with the
    name of the object in the user script. The type must include `str`.

- `is_path` : whether the parameter is a path. If so, this file/folder will be uploaded to the host system.

- `description` : description of the parameter

- `default_value`: default value for the parameter. This value is used as the default if `disable_search=False` or there are no searchable values.
    Must be the same type as the parameter or a ConditionalDefault SearchParameter.

- `searchable_values`: default searchable values for the parameter. This value is used as the default if `disable_search=True`.
    Must be a Categorical or Conditional SearchParameter.

### Example
```python
    @staticmethod
    def _default_config() -> Dict[str, PassConfigParam]:
        return {
            # required parameter
            "param1": PassConfigParam(type_=int, required=True, description="param1 description"),
            # optional parameter with default value
            "param2": PassConfigParam(type_=int, default_value=1, description="param2 description"),
            # optional parameter with default value and searchable values
            "param3": PassConfigParam(
                type_=int, default_value=1, searchable_values=Categorical([1, 2, 3]), description="param3 description"
            ),
            # optional parameter with `is_object` set to True
            # the value of this parameter can be a string or a function that takes a string and returns the object,
            # say a class ObjectClass
            "param4": PassConfigParam(
                type_=Union[str, Callable[[str], Pass]], is_object=True, description="param4 description"
            ),
            # optional parameter with default_value that depends on another parameter value
            "param5": PassConfigParam(
                type_=int,
                default_value=ConditionalDefault(parents="param2", support={(1,): 2, (2,): 3}, default=4),
                description="param5 description",
            ),
            # optional parameter with searchable_values that depends on other parameter values
            "param6": PassConfigParam(
                type_=int,
                default_value=1,
                searchable_values=Conditional(
                    parents=("param2", "param3"),
                    # invalid if (param2, param3) not in [(1, 1), (1, 2)]
                    support={
                        (1, 1): Categorical([1, 2, 3]),
                        (1, 2): Categorical([4, 5, 6]),
                    },
                ),
                description="param6 description",
            ),
        }

```

### 3. Implement the run function

The final step is to implement the `_run_for_config` method to optimize the input model. Olive Engine will invoke the
method while auto tuning the model. This method will also receive a search point (one set of configuration option from
the search space created based on the options defined in `_default_config()`) along with output path. The method
should return a valid OliveModel which can be used as an input for the next Pass.

```python
    def _run_for_config(self, model: ONNXModel, config: Dict[str, Any], output_model_path: str) -> ONNXModel:
```