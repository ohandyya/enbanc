# Work Journal

## Future Enhancement

1. How do we leverage AI to interactively create `Statue`?

2. How do we leverage AI to update/fine-tune the instructions of AI agents?

3. How to support re-hear with new informaiton?

    - Is this a legit use case at all?

    - Persisted evidence store

## To Dos

## Daily Log

### Sep 1

#### Key Questions

1. What is the desired usage of the API?

    - [Done] What shall the package do?

    - [Done] How to use it?

    - What is the Input/Output schema (requrie pydantic schema)

    - [Done] History tracking

        - What to explose in the API?

    - [Leave for future] How does `create_rule` work? Shall we leave this to future?

2. Accuracy Evaluation

    - Where can we find the dataset for evaluation? Kaggle?

        - Ideally, we want to run accuracy against different dataset that makes practical use case

    - The `rule` plays to pivotal role in the accuracy. So we need to consider the `rule` as part of the accuracy evaualtion.
