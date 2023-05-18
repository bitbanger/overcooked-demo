# htn-parser
This repo contains the code for VAL, the Verbal Apprentice Learner. The VAL code is encapsulated by the ITL class defined in itl.py.

## Using VAL
To use VAL, instantiate the ITL class by passing it a comma-separated string of "primitive actions" available in your system.
These actions are underscore-separated predicate names with generalized argument variables, coupled with verbal descriptions used to help VAL's GPT-based dialog interpreter select the right actions from dialog.

### How to import the ITL class
Unfortunately, due to my lack of understanding of what I was doing, I included a hyphen in this repo name. This ended up being one of the worst decisions I've ever made, because Python package names don't like to have hyphens in them.

As a result, when you clone this module into a folder within your own project directory and try to import the ITL class from that folder, you'll have to do something like this:

```python
import importlib
itl = importlib.import_module('htn-parser.itl').InteractiveTaskLearner(YOUR_PRIM_VALUE_STR)
```

I'm sorry. I'll change the repo name at some point, probably.

### primitive_actions example
VAL's output is ultimately a sequence of primitive actions that you can apply to your environment. They (the output items) will be strings taking the following form:
```
PRED1 arg1 arg2
PRED2 arg1
...
```

To tell VAL what primitive actions are available in your environment, you will pass a string into the constructor of the
```ITL``` class. An example of a primitive_actions string value passed to ```ITL```:

```moveToObject(<object>) - move over to an object,interactWithObject() - press the space button to interact with whatever you're facing```

The two predicate names here, ```moveToObject``` and ```interactWithObject```, take one and zero arguments, respectively. Each is coupled, separated by two spaces with a hyphen in between them, from its respective verbal description. These are optional, and you can just write "an action" if you want; indeed, right now, all learned actions are given the description "a learned action". However, the theory is that these descriptions help GPT decode the meaning of the predicates and select them when semantically similar dialog is encountered.

### Obtaining output from VAL
When you're at a point in your own game/environment where you want to prompt a user for a dialog instruction, obtain that dialog as text (e.g., via an ```input()``` function) and make the following call to your initialized ITL object:

```python
itl.process_instruction(INSTRUCTION_TEXT)
```

The ```process_instruction``` function has an optional keyword argument, ```clarify_hook```, which accepts a function value. By default, when VAL doesn't know what one of the actions in the dialog instruction means, it will ask for a clarification as another line of dialog by printing its request to ```STDOUT``` and reading the response from the user from ```STDIN```. The ```clarify_hook``` argument allows you to pass in a function that accepts the unknown predicate as an argument and returns the clarifying line of dialog as a string, so that you can integrate this into your environment however you want.

```process_instruction``` returns a list of primitive actions and arguments, as seen above in the prior subsection. So, how should you use these?

### Using output from VAL

It's up to you to decide what these strings mean. In the Overcooked environment, for example, the two primitive actions are "moveTo" and "interact", and when the game code receives these, it translates them into specific input combinations I decided on and coded into the game logic.

Remember that VAL is currently just a system for translating dialog into these primitive action sequences: you can call it as a function within your game logic, and then interpret its output however you want.

### Saving and loading VAL models
VAL automatically stores learned actions with generalized arguments for re-use. As a result, you may want to save the VAL model and re-load it so that your future sessions can use the accumulated task knowledge. This is easy to do.

For saving:

```python
itl.save(OUTPUT_FILENAME)
```

For loading:

```python
itl = ITL.load(INPUT_FILENAME)
```


## Conclusion

Please reach out to me by email (```lanetrain@gatech.edu```) or on Slack if you have any questions!
