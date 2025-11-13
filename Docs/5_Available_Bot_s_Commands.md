# Available Commands

## Phonebook

- **add-contact**: add new contact or update existing with additional phone number
  - Usage: `add-contact "Name" [0123456789]`

- **change-phone**: change contact's phone number
  - Usage: `change-phone "Name" old10 new10`

- **show-phone**: show contact's phone numbers
  - Usage: `show-phone "Name"`

- **all-contacts**: show all contacts from storage
  - Usage: `all-contacts`

- **add-birthday**: add contact's birthday
  - Usage: `add-birthday "Name" DD.MM.YYYY`

- **show-birthday**: show contact's birthday
  - Usage: `show-birthday "Name"`

- **birthdays**: show upcoming birthdays (within 7 days)
  - Usage: `birthdays`

- **add-email**: add contact's email
  - Usage: `add-email "Name" example@mail.com`

- **delete-email**: delete contact's email
  - Usage: `delete-email "Name" example@mail.com`

- **add-address**: set contact's address
  - Usage: `add-address "Name" "Kyiv, ..."`

- **delete-address**: delete contact's address
  - Usage: `delete-address "Name"`

- **delete-phone**: delete contact's phone number
  - Usage: `delete-phone "Name" 0123456789`

- **find-contact**: search contacts by field value
  - Usage: `find-contact query`

- **delete-contact**: delete the whole contact with all fields
  - Usage: `delete-contact "Name"`

## Notes

- **add-note**: add note with title
  - Usage: `add-note "Title" text...`

- **all-notes**: show all notes (sort by title or created)
  - Usage: `all-notes [title|created]`

- **find-note**: find note by text query
  - Usage: `find-note query`

- **find-tag**: find notes by tag
  - Usage: `find-tag tag`

- **edit-note**: edit a note's content by its title
  - Usage: `edit-note "Title" new_text...`

- **add-tags**: add tags to note by its title
  - Usage: `add-tags "Title" tag1 tag2 ...`

- **delete-tag**: delete tag from note by its title
  - Usage: `delete-tag "Title" tag`

- **delete-note**: delete note by its title
  - Usage: `delete-note "Title"`

## System

- **hello**: greetings from the bot
  - Usage: `hello`

- **help**: show all available commands with their descriptions
  - Usage: `help [command]`

- **close**: close the program
  - Usage: `close`

- **exit**: close the program
  - Usage: `exit`

- **version**: show current version and storage path
  - Usage: `version`
