import { isFunction, isString, filter, map } from "lodash";
import React, { useState, useCallback, useEffect } from "react";
import PropTypes from "prop-types";
import classNames from "classnames";
import Input from "antd/lib/input";
import AntdMenu from "antd/lib/menu";
import Link from "@/components/Link";
import TagsList from "@/components/TagsList";

/*
    SearchInput
 */

export function SearchInput({
  placeholder,
  value,
  showIcon,
  onChange,
  label,
  className,
  liveSearch = true,
}) {
  const [currentValue, setCurrentValue] = useState(value);

  useEffect(() => {
    setCurrentValue(value);
  }, [value]);

  const commitSearch = useCallback(
    searchValue => {
      const nextValue = (searchValue ?? "").trim();
      setCurrentValue(nextValue);
      onChange(nextValue);
    },
    [onChange]
  );

  const onInputChange = useCallback(
    event => {
      const newValue = event.target.value;
      setCurrentValue(newValue);
      if (liveSearch || newValue === "") {
        onChange(newValue);
      }
    },
    [onChange, liveSearch]
  );

  const searchControl = showIcon ? (
    <Input.Search
      allowClear
      autoFocus={false}
      className={className}
      placeholder={placeholder}
      value={currentValue}
      aria-label={label}
      onChange={onInputChange}
      onSearch={commitSearch}
    />
  ) : (
    <Input
      allowClear
      autoFocus={false}
      className={className}
      placeholder={placeholder}
      value={currentValue}
      aria-label={label}
      onChange={onInputChange}
      onPressEnter={() => commitSearch(currentValue)}
    />
  );

  if (className) {
    return searchControl;
  }

  return <div className="m-b-10">{searchControl}</div>;
}

SearchInput.propTypes = {
  value: PropTypes.string.isRequired,
  placeholder: PropTypes.string,
  showIcon: PropTypes.bool,
  onChange: PropTypes.func.isRequired,
  label: PropTypes.string,
  className: PropTypes.string,
  liveSearch: PropTypes.bool,
};

SearchInput.defaultProps = {
  placeholder: "Search...",
  showIcon: false,
  label: "Search",
  className: null,
  liveSearch: true,
};

/*
    Menu
 */

export function Menu({ items, selected }) {
  items = filter(items, item => (isFunction(item.isAvailable) ? item.isAvailable() : true));
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="m-b-10 tags-list tiled">
      <AntdMenu
        className="invert-stripe-position"
        mode="inline"
        selectable={false}
        selectedKeys={[selected]}
        items={map(items, item => ({
          key: item.key,
          className: "m-0",
          label: (
            <Link href={item.href}>
              {isString(item.icon) && item.icon !== "" && (
                <span className="btn-favorite m-r-5">
                  <i className={item.icon} aria-hidden="true" />
                </span>
              )}
              {isFunction(item.icon) && (item.icon(item) || null)}
              {item.title}
            </Link>
          ),
        }))}
      />
    </div>
  );
}

Menu.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      href: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      icon: PropTypes.func, // function to render icon
      isAvailable: PropTypes.func, // return `true` to show item and `false` to hide; if omitted: show item
    })
  ),
  selected: PropTypes.string,
};

Menu.defaultProps = {
  items: [],
  selected: null,
};

export function FilterMenu({ items, selected }) {
  items = filter(items, item => (isFunction(item.isAvailable) ? item.isAvailable() : true));
  if (items.length === 0) {
    return null;
  }

  return (
    <nav className="list-page-filter-menu" aria-label="List filters">
      {map(items, item => (
        <Link
          key={item.key}
          href={item.href}
          className={classNames("list-page-filter-menu__item", {
            "list-page-filter-menu__item--active": item.key === selected,
          })}
        >
          {isString(item.icon) && item.icon !== "" && (
            <span className="btn-favorite">
              <i className={item.icon} aria-hidden="true" />
            </span>
          )}
          {isFunction(item.icon) && (item.icon(item) || null)}
          {item.title}
        </Link>
      ))}
    </nav>
  );
}

FilterMenu.propTypes = {
  items: Menu.propTypes.items,
  selected: PropTypes.string,
};

FilterMenu.defaultProps = {
  items: [],
  selected: null,
};

/*
    MenuIcon
 */

export function MenuIcon({ icon }) {
  return (
    <span className="btn-favorite m-r-5">
      <i className={icon} aria-hidden="true" />
    </span>
  );
}

MenuIcon.propTypes = {
  icon: PropTypes.string.isRequired,
};

/*
    ProfileImage
 */

export function ProfileImage({ user }) {
  if (!isString(user.profile_image_url) || user.profile_image_url === "") {
    return null;
  }
  return <img src={user.profile_image_url} className="profile__image--sidebar m-r-5" width="13" alt={user.name} />;
}

ProfileImage.propTypes = {
  user: PropTypes.shape({
    profile_image_url: PropTypes.string,
    name: PropTypes.string,
  }).isRequired,
};

/*
    Tags
 */

export function Tags({ url, onChange, showUnselectAll, layout, selectedTags }) {
  if (url === "") {
    return null;
  }
  return (
    <div className={classNames(layout === "inline" ? "tags-list--inline-wrapper" : "m-b-10")}>
      <TagsList
        tagsUrl={url}
        onUpdate={onChange}
        showUnselectAll={showUnselectAll}
        layout={layout}
        selectedTags={selectedTags}
      />
    </div>
  );
}

Tags.propTypes = {
  url: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  showUnselectAll: PropTypes.bool,
  layout: PropTypes.oneOf(["sidebar", "inline"]),
  selectedTags: PropTypes.arrayOf(PropTypes.string),
};

Tags.defaultProps = {
  showUnselectAll: false,
  layout: "sidebar",
  selectedTags: undefined,
};
