def rreplace(s, old, new, count=-1):
    """
    Replace occurrences of 'old' with 'new' in the string 's', starting from the right.
    
    Parameters:
    - s (str): The original string.
    - old (str): The substring to be replaced.
    - new (str): The substring to replace with.
    - count (int): The number of occurrences to replace from the right. Default is -1, which replaces all occurrences.
    
    Returns:
    - str: The modified string with replacements made from the right.
    """
    if count == -1:
        return new.join(s.rsplit(old))
    else:
        return new.join(s.rsplit(old, count))