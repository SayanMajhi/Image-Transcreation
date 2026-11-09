# SmolVLM truncation comparison

[Original paired results](../vlm_comparison/comparison.json) | [New measured records](smol_extended.json) | [Updated blank worksheet](review.md)

Only the five selected images ran; no Florence, completed SmolVLM or sanity/warmup inference. The first extended inference is cold; original collection timings followed warmup. Loading is excluded from inference; CUDA allocated peaks include resident weights. The assembled worksheet mixes retained 128-token results and selective 256-token reruns.

Blank manual scores. Reaching EOS or adding text does not establish greater accuracy.

Extended captions reaching EOS: 0/5. Unresolved captions in the review set: 5.

| Image | Original tokens | New tokens | New EOS | Ceiling reached | Suspected truncation | Original ms | New ms | New peak CUDA MiB | Original text prefix retained |
| --- | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| scene_01 | 128 | 256 | False | True | True | 5978.22 | 12252.89 | 1124.13 | True |
| scene_05 | 128 | 256 | False | True | True | 7655.52 | 12241.53 | 1124.13 | True |
| scene_07 | 128 | 256 | False | True | True | 6192.10 | 11805.94 | 1124.13 | True |
| scene_08 | 128 | 256 | False | True | True | 6218.50 | 11638.34 | 1124.13 | True |
| scene_09 | 128 | 256 | False | True | True | 6743.70 | 11774.36 | 1124.13 | True |

## scene_01

**Original (128-token ceiling):**

The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess&#x27;s power or attributes.

The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings

**Extended (256-token ceiling):**

The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess&#x27;s power or attributes.

The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings or incense sticks, in their hands. These objects are placed on a platform or a large, flat surface, which may be a stage or a platform for the goddess&#x27;s worship. The people are dressed in traditional Indian attire, which includes long, colorful saris.

In the background, there are trees and what appears to be a building or a structure, suggesting that the scene is taking place in a temple or a sacred site. The sky is partially visible, with some clouds, indicating that the scene is likely taking place during a religious or cultural event.

The image conveys a sense of reverence and devotion, as the people

## scene_05

**Original (128-token ceiling):**

The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.

Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with

**Extended (256-token ceiling):**

The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.

Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with fresh apples, which are likely part of the fruit selection.

To the left of the bowl, there is a basket containing a variety of fruits, including bananas, apples, and possibly other types of produce. The bananas are prominently displayed, and they are accompanied by a small bowl filled with a green leafy vegetable, possibly a type of lettuce or spinach.

To the right of the bowl, there is a bowl filled with a variety of fruits, including bananas, apples, and possibly other types of produce. The bowl is also adorned with a decorative element, possibly a flower or a small plant, adding a touch of nature to

## scene_07

**Original (128-token ceiling):**

The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.

In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils.

**Extended (256-token ceiling):**

The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.

In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils. The fire is small, and it is not actively burning, indicating that it is not the primary source of heat for the room.

To the right of the fire pit, there is a woman seated on a raised platform. She is wearing a traditional outfit, which includes a long, loose-fitting garment with a patterned design and a headscarf. The woman is engaged in a ritual or activity, possibly cooking or preparing food. She is holding a long, thin cooking utensil, which appears to be a ladle or a spoon, and is stirring or stirring something in a pot or pan.

The room is furnished

## scene_08

**Original (128-token ceiling):**

In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the

**Extended (256-token ceiling):**

In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt

## scene_09

**Original (128-token ceiling):**

The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:

1. **People**: There are three individuals in the image. 
   - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.
   - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.
   - **Person Behind the Person Behind the Person**: This

**Extended (256-token ceiling):**

The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:

1. **People**: There are three individuals in the image. 
   - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.
   - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.
   - **Person Behind the Person Behind the Person**: This person is standing behind the person in the back. They are wearing a dark-colored garment, possibly a coat or a sweater.

2. **Cooking Area**:
   - **Table**: In the foreground, there is a table with various items on it. The table is covered with a white cloth.
   - **Baskets**: There are two baskets on the table. One basket is filled with food items, possibly bread or other types of bread. The other basket is empty.
   - **Cooking Tools**: There are some cooking tools on the table, including a large knife and a bowl.

3. **

Changed, longer or complete text is not automatically more accurate. Inspect visible evidence, new unsupported claims and omissions manually.
