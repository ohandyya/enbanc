# Work Journal

## Future Enhancement

1. How do we leverage AI to interactively create `Statue`?

2. How do we leverage AI to update/fine-tune the instructions of AI agents?

3. How to support re-hear with new informaiton?

    - Is this a legit use case at all?

    - Persisted evidence store

4. Use AI to build `API References`

    - Even better: find a way to publish it.

## To Dos

1. [Done] How to design tools an how to allow user to extend the tool?

    - What is a good interface?

    - How can user extend?

    - What are the default tools that we can build? Just web?

2. Design docs/design/execution.md

3. After all desings are done, cut a new release, 0.0.x.


## Questions

1. How to organize implementation plan?

2. How to design accuracy evaluation

    - What possible datasets can we use?

3. How to trimp the dependencies

    - We `enbanc` to receive maximum adoption. So, we watn to reduce the dependencies.

    - For pydantic-ai, can we use just the core?
    - For tavily, I want it to be optional. If `tavily` is not installed, it shall raise an exception when user tries to use the tavily tool. But if user did not use the tavily tool, it should continue to work. Can we do this in the form of optional package?

## Daily Log

### Sep 5

#### Execution

- We still want user to set a `global budget` similar to ` budget=UsageLimits(cost_limit=Decimal("2.00"))`. The execution must support that.

### Setp 4

#### Prompts

- What I want regarding the promping

    - When user create a statue, the statue must be used as `part of the prompt` sent to both the judge and all the advocates. This is because the statue is the rulling logic.

    - Each advocate need to argument baed on the assigned verdict, so this means which verdict it is advocating for should be part of the prompt for each advocate.

    - the enbanc package (maybe in Tribunal) must include the prompts to ensure the tribunal ordering. For exaple, the judge needs to know that he/she is the judge and there are several advocates. The advocates need to know they are advocates and there is judge. Basically, the process defined in docs/design/tribunal.md should a knowledge that judge and advocates knows. And this should be auto-injected by the enbanc package. User should NOT write any of these.

### Sep 1

#### Key Questions

1. What is the desired usage of the API?

    - [Done] What shall the package do?

    - [Done] How to use it?

    - [Done] What is the Input/Output schema (requrie pydantic schema)

    - [Done] History tracking

        - What to explose in the API?

    - [Leave for future] How does `create_rule` work? Shall we leave this to future?

2. Accuracy Evaluation

    - Where can we find the dataset for evaluation? Kaggle?

        - Ideally, we want to run accuracy against different dataset that makes practical use case

    - The `rule` plays to pivotal role in the accuracy. So we need to consider the `rule` as part of the accuracy evaualtion.
