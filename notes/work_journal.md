# Work Journal

## Future Enhancement

1. How do we leverage AI to interactively create `Statue`?

2. How do we leverage AI to update/fine-tune the instructions of AI agents?

3. How to support re-hear with new informaiton?

    - Is this a legit use case at all?

    - Persisted evidence store

## To Dos

1. How to design accuracy evaluation

    - What possible datasets can we use?

2. [Done] How to design tools an how to allow user to extend the tool?

    - What is a good interface?

    - How can user extend?

    - What are the default tools that we can build? Just web?

3. After all desings are done, cut a new release, 0.0.x.

4. Ask AI if we are missing any important `decisions` before we can move on to implementations.

## Questions

1. How to organize implementation plan?

## Daily Log

### Setp 4


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
