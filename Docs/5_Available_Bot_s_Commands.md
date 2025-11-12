Available Commands:



ContactBook:

 - add  **--> add-contact**: add new contact or update existing with additional phone number: **add-contact** "Name" \[0123456789]

 - add-birthday: add contact's birthday : add-birthday "Name" DD.MM.YYYY

 - add-email: add contact's emails: add-email "Name" example@mail.com

 - all  **--> all-contacts**: show all contacts from storage: **all-contacts**

  - birthdays: show birthdays within 7 days period: birthdays

  - change **--> change-phone**: change contact's phone: **change-phone** "Name" \[old10] \[new10]

  - delete-contact: delete the whole contact with all fields : delete-contact "Name"

  - find **--> find-contact**: contact's search based on contact's field value: **find-contact** field value]

  - phone: **--> show-phone** show contact's phones: **show-phone** "Name"

  - remove-email **--> delete-email**: delete contact's email: **delete-email** "Name" example@mail.com

  - set-address: set contact's address: set-address "Name" "Kyiv, ..."

  - show-birthday: show contact's birthday: show-birthday "Name"



Notes:

  - add-note: add note with title: add-note "Title" текст...

  - delete-note: delete note by it's title: delete-note "Title"

  - edit-note: edit a note's content by its title: edit-note "Title" новий\_текст...

  - find-note: find note by query: find-note query

  - find-tag: find notes by tag: find-tag tag

  - list-notes  **--> all-notes**: show all notes: **all-notes** \[title|created]

  - tag-add **--> add-tags**: add tags by their title: **add-tags** "Title" tag1 tag2 ...

  - tag-remove **--> delete-tag**: delete tag by it's title: **delete-tag** "Title" tag



System:

  - close: close the program

  - exit: close the program

  - hello: greetings from the bot

  - help: show all available commands with their descriptions

  - version: show current version

