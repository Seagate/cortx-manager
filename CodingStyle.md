# Coding Guidelines

The CORTX Manager is a backend application that is built on [Python](https://www.python.org/dev/peps/pep-0008/). 

We've listed the coding style that is specific to any submissions made to the CORTX Manager Repository.

## File Names

-   All small case letters in the file name
-   Separator: “_” 
-   **Example:** `some_file.py`

## Indentation

-   Use 4 spaces per indentation level.

-   Continuation lines should align wrapped elements either vertically using Python's implicit line joining inside parentheses, brackets, and braces 
or using a hanging indent.

-   Add 4 spaces - an extra level of indentation to distinguish arguments from the rest.

  ```python
  def long_function_name(
        var_one, var_two, var_three,
        var_four):
    print(var_one)
    ```

-   Hanging indents should add a level.

  ```python
    foo = long_function_name(
    var_one, var_two,
    var_three, var_four)
  ```

-   Line length restriction to be 100 characters.
-   Break Characters before binary operators, after comma and Brackets
-   Use ‘...’  by default for strings.

## Imports

-   Imports should usually be on separate lines.
  
  **Incorrect method:** `import sys, os, time` 
  **Correct method:**
  
  ```python
  import sys
  import os
  import time
  ```

-   Imports are always put at the top of the file, after any module comments and docstrings, and before module globals and constants.
-   Imports should be grouped in the following order:
-   Standard library imports.
-   Related third party imports.
-   Local application/library specific imports.
-   You should put a blank line between each group of imports.

## Docstrings

-   It is mandatory to have comments/docstrings attached to each and every function except for @property or equivalent.

-   Docstrings should be informative.

-   Follow the following Format 

    ```python
    def complex(real=0.0:float, imag=0.0: float) -> str:
    
    """
    Text description of what function does

       :param real:Real Number  
       :param imag:  imaginary number 
       :return:  Returns Complex value 
     """
     
       if imag == 0.0 and real == 0.0:
       return complex_zero
    ```

## Typings

Follow [3.6 Typings in Python](https://www.python.org/dev/peps/pep-0484/) to define function and methods as it enables easy understanding of the data fetched in a function

```python
def greeting(name: str) -> str:
return 'Hello ' + name
```

## String Concatenation

[Python 3.6](https://www.python.org/dev/peps/pep-0498/) supports `f` string hence using `f` strings format is preferred than adding two strings as they create an extra object. 

**Example: 1**

```python
import datetime
name = 'Fred'
age = 50
anniversary = datetime.date(1991, 10, 12)
```

**Example 2:**

```python
f'My name is {name}, my age next year is {age+1}, my anniversary is {anniversary:%A, %B %d, %Y}.'
```

**Example: 3**

```python
'My name is Fred, my age next year is 51, my anniversary is Saturday, October 12, 1991.'
```

**Example: 4**

```python
f'He said his name is {name!r}.'
```
