DROP TABLE IF EXISTS Assassins;
DROP TABLE IF EXISTS Admins;
DROP TABLE IF EXISTS Games;

create table Admins
(
    id INTEGER
        primary key
        unique
);

create table Games
(
    id               INTEGER
        primary key
        unique,
    game_master_id   INTEGER
        unique,
    game_master_user VARCHAR(45)
        unique,
    started          INTEGER default 0 not null,
    free_for_all     INTEGER default 0 not null
);

create table Assassins
(
    id            INTEGER     not null
        primary key
        unique,
    name          VARCHAR(45) not null,
    code_name     VARCHAR(45) not null,
    address       VARCHAR(45) not null,
    major         VARCHAR(45) not null,
    needs_weapon  INTEGER     not null,
    presumed_dead INTEGER default 0 not null,
    target        INTEGER default NULL,
    tally         INTEGER default 0 not null,
    task_answered INTEGER default 0 not null,
    jokers_used   INTEGER default 0 not null,
    game          INTEGER     not null
        references Games
);

insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (1, 'Bssassin', 'Bss', 'Bss Str. 1', 'Bdvanced assassination', 0, 111);

insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (2, 'Cssassin', 'Css', 'Css Str. 1', 'Cdvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (3, 'Dssassin', 'Dss', 'Dss Str. 1', 'Ddvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (4, 'Essassin', 'Ess', 'Ess Str. 1', 'Edvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (5, 'Fssassin', 'Fss', 'Fss Str. 1', 'Fdvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (6, 'Gssassin', 'Gss', 'Gss Str. 1', 'Gdvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (7, 'Hssassin', 'Hss', 'Hss Str. 1', 'Hdvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (8, 'Issassin', 'Iss', 'Iss Str. 1', 'Idvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (9, 'Jssassin', 'Jss', 'Jss Str. 1', 'Jdvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (10, 'Kssassin', 'Kss', 'Kss Str. 1', 'Kdvanced assassination', 0, 111);


insert into Assassins (id, name, code_name, address, major, needs_weapon, game)
values (11, 'Lssassin', 'Lss', 'Lss Str. 1', 'Ldvanced assassination', 0, 111);

insert into Games (id, game_master_id, game_master_user) values (111, 123123123, 'someone_has_this');

UPDATE Assassins SET target=3 where id=2;
UPDATE Assassins SET target=4 where id=3;
UPDATE Assassins SET target=5 where id=4;
UPDATE Assassins SET target=6 where id=5;
UPDATE Assassins SET target=7 where id=6;
UPDATE Assassins SET target=8 where id=7;
UPDATE Assassins SET target=9 where id=8;
UPDATE Assassins SET target=10 where id=9;
UPDATE Assassins SET target=11 where id=10;
UPDATE Assassins SET target=1 where id=11;